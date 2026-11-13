from typing import TYPE_CHECKING, Any, Callable, Dict, List, Optional, Sequence, cast

import pydantic
from asgiref.sync import sync_to_async
from django.http import HttpRequest, HttpResponse, JsonResponse

from ninja.conf import settings as ninja_settings
from ninja.constants import NOT_SET
from ninja.errors import (
    ConfigError,
    HttpError,
    ValidationError,
    ValidationErrorContext,
)
from ninja.operation import authenticate_async, check_throttles
from ninja.renderers import BaseRenderer
from ninja.security.apikey import APIKeyCookie
from ninja.signature import ViewSignature, is_async
from ninja.throttling import BaseThrottle
from ninja.types import DictStrAny
from ninja.websockets.connection import WebSocket
from ninja.websockets.handshake import (
    UPGRADE_NOT_HANDLED_DETAIL,
    WEBSOCKET_ONLY_DETAIL,
    origin_is_allowed,
    reject,
)
from ninja.websockets.types import WebSocketException

if TYPE_CHECKING:
    from ninja import NinjaAPI  # pragma: no cover

__all__ = ["WebSocketOperation"]

_ALLOWED_PARAM_SOURCES = {"path", "query", "header", "cookie"}


class WebSocketOperation:
    """
    A websocket endpoint registered with ``@api.websocket(path)``.

    Handlers must be ``async def`` and receive the connection through a
    parameter annotated with :class:`ninja.WebSocket`. Path, Query, Header and
    Cookie params are resolved from the handshake exactly like HTTP operations.
    """

    def __init__(
        self,
        path: str,
        view_func: Callable[..., Any],
        *,
        auth: Any = NOT_SET,
        throttle: Any = NOT_SET,
        check_origin: Optional[bool] = None,
        url_name: Optional[str] = None,
    ) -> None:
        if not is_async(view_func):
            raise ConfigError(
                f"WebSocket handler '{view_func.__name__}' must be an 'async def' function"
            )
        self.path = path
        self.view_func = view_func
        self.api: NinjaAPI = cast("NinjaAPI", None)
        self.url_name = url_name

        self.auth_param: Any = auth
        self.auth_callbacks: Sequence[Callable[..., Any]] = []
        self._set_auth(auth)

        # None: use settings.NINJA_WEBSOCKET_CHECK_ORIGIN
        self.check_origin = check_origin

        if isinstance(throttle, BaseThrottle):
            throttle = [throttle]
        self.throttle_param = throttle
        self.throttle_objects: List[BaseThrottle] = []
        if throttle is not NOT_SET:
            for th in throttle:
                assert isinstance(th, BaseThrottle), (
                    "Throttle should be an instance of BaseThrottle"
                )
                self.throttle_objects.append(th)

        self.signature = ViewSignature(path, view_func)
        if self.signature.websocket_arg is None:
            raise ConfigError(
                f"WebSocket handler '{view_func.__name__}' must declare a parameter "
                "annotated with 'WebSocket' (e.g. 'websocket: WebSocket')"
            )
        for model in self.signature.models:
            source = model.__ninja_param_source__
            if source not in _ALLOWED_PARAM_SOURCES:
                raise ConfigError(
                    f"WebSocket handler '{view_func.__name__}' cannot use '{source}' "
                    "params: only Path, Query, Header and Cookie are available "
                    "during the handshake. Use websocket.receive_json() instead."
                )
        if "request" in self.signature.signature.parameters:
            raise ConfigError(
                f"WebSocket handler '{view_func.__name__}' declares a 'request' "
                "parameter: websocket handlers receive only the WebSocket, use "
                "'websocket.request' to access the handshake request"
            )
        self.models = self.signature.models

    def _set_auth(self, auth: Any) -> None:
        if auth is not None and auth is not NOT_SET:
            self.auth_callbacks = isinstance(auth, Sequence) and auth or [auth]

    def clone(self) -> "WebSocketOperation":
        cloned = object.__new__(self.__class__)
        cloned.__dict__.update(self.__dict__)
        cloned.api = cast("NinjaAPI", None)
        cloned.auth_callbacks = list(self.auth_callbacks)
        cloned.throttle_objects = list(self.throttle_objects)
        return cloned

    def get_http_view(self) -> Callable[..., HttpResponse]:
        """
        The Django view mounted at this path in ``api.urls``.

        Real websocket connections never reach it when the ninja ASGI app is
        used: it only answers plain HTTP requests (426 Upgrade Required) and
        explains the ASGI requirement when an upgrade request arrives through
        Django's HTTP stack (WSGI server, or ASGI without the ninja wrapper).
        """
        operation = self

        def websocket_http_view(
            request: HttpRequest, *args: Any, **kwargs: Any
        ) -> HttpResponse:
            return operation.http_response(request)

        websocket_http_view.csrf_exempt = True  # type: ignore
        websocket_http_view.ninja_websocket_operation = operation  # type: ignore
        websocket_http_view.ninja_websocket_only = True  # type: ignore
        return websocket_http_view

    def http_response(self, request: HttpRequest) -> HttpResponse:
        if request.headers.get("upgrade", "").lower() == "websocket":
            detail = UPGRADE_NOT_HANDLED_DETAIL
        else:
            detail = WEBSOCKET_ONLY_DETAIL
        # Note: 'Upgrade'/'Connection' headers are hop-by-hop and rejected by
        # WSGI servers (wsgiref), so only the status code and body are sent.
        return JsonResponse({"detail": detail}, status=426)

    def _get_values(self, request: HttpRequest, path_params: DictStrAny) -> DictStrAny:
        values: DictStrAny = {}
        error_contexts: List[ValidationErrorContext] = []
        for model in self.models:
            try:
                values.update(model.resolve(request, self.api, path_params))
            except pydantic.ValidationError as e:
                error_contexts.append(
                    ValidationErrorContext(pydantic_validation_error=e, model=model)
                )
        if error_contexts:
            raise self.api.validation_error_from_error_contexts(error_contexts)
        return values

    def _requires_origin_check(self) -> bool:
        if any(isinstance(cb, APIKeyCookie) and cb.csrf for cb in self.auth_callbacks):
            # cookie auth asked for CSRF protection: never skip it
            return True
        if self.check_origin is not None:
            return self.check_origin
        return ninja_settings.WEBSOCKET_CHECK_ORIGIN

    def response_for_exception(
        self, request: HttpRequest, exc: Exception
    ) -> Optional[HttpResponse]:
        """
        The response the API exception handlers produce for ``exc``, or None
        when no handler deals with it (it re-raises, e.g. with DEBUG=False).
        """
        try:
            return self.api.on_exception(request, exc)
        except Exception as raised:
            if raised is exc:
                return None
            raise

    async def _authenticate(self, websocket: WebSocket) -> Optional[Exception]:
        request = websocket.request
        error = await authenticate_async(self.auth_callbacks, request)
        if isinstance(error, WebSocketException):
            raise error  # closes with its own code (see ninja.asgi)
        if error is None:
            websocket.auth = request.auth  # type: ignore[attr-defined]
        return error

    async def _reject_with(self, websocket: WebSocket, exc: Exception) -> None:
        response = self.response_for_exception(websocket.request, exc)
        if response is None:
            raise exc
        await reject(websocket, response)

    async def run(self, websocket: WebSocket, path_params: Dict[str, Any]) -> None:
        """
        Process the handshake (origin, auth, throttling, params) and call the
        handler. Rejections are built by the API exception handlers, so custom
        handlers and renderers apply like for HTTP operations.
        """
        request = websocket.request
        websocket.path_params = path_params
        if _is_json_renderer(self.api.renderer):
            websocket.renderer = self.api.renderer
        # Browsers send cookies on cross-site websocket handshakes and Django's
        # CSRF check does not protect GET requests: the Origin check replaces it.
        request._ninja_csrf_exempt = True  # type: ignore[attr-defined]

        if self._requires_origin_check() and not origin_is_allowed(request):
            await self._reject_with(websocket, HttpError(403, "Origin not allowed"))
            return

        if self.auth_callbacks:
            error = await self._authenticate(websocket)
            if error is not None:
                await self._reject_with(websocket, error)
                return

        if self.throttle_objects:
            response = await sync_to_async(check_throttles)(
                self.api, self.throttle_objects, request
            )
            if response is not None:
                await reject(websocket, response)
                return

        try:
            values = self._get_values(request, path_params)
        except ValidationError as e:
            await self._reject_with(websocket, e)
            return

        values[cast(str, self.signature.websocket_arg)] = websocket
        await self.view_func(**values)


def _is_json_renderer(renderer: BaseRenderer) -> bool:
    media_type = (renderer.media_type or "").split(";")[0].strip().lower()
    return media_type == "application/json" or media_type.endswith("+json")
