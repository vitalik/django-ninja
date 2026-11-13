import inspect
from typing import TYPE_CHECKING, Any, Callable, Dict, List, Optional, Sequence, cast

import pydantic
from asgiref.sync import sync_to_async
from django.http import HttpRequest, HttpResponse, JsonResponse

from ninja.constants import NOT_SET
from ninja.errors import (
    AuthenticationError,
    ConfigError,
    HttpError,
    ValidationError,
    ValidationErrorContext,
)
from ninja.security.apikey import APIKeyCookie
from ninja.signature import ViewSignature, is_async
from ninja.types import DictStrAny
from ninja.utils import is_async_callable
from ninja.websockets.connection import WebSocket
from ninja.websockets.handshake import (
    UPGRADE_NOT_HANDLED_DETAIL,
    WEBSOCKET_ONLY_DETAIL,
    deny,
    origin_is_allowed,
)

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
        self.models = self.signature.models
        self._pass_request = "request" in self.signature.signature.parameters

    def _set_auth(self, auth: Any) -> None:
        if auth is not None and auth is not NOT_SET:
            self.auth_callbacks = isinstance(auth, Sequence) and auth or [auth]

    def clone(self) -> "WebSocketOperation":
        cloned = object.__new__(self.__class__)
        cloned.__dict__.update(self.__dict__)
        cloned.api = cast("NinjaAPI", None)
        cloned.auth_callbacks = list(self.auth_callbacks)
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
        return any(
            isinstance(cb, APIKeyCookie) and cb.csrf for cb in self.auth_callbacks
        )

    async def _authenticate(self, websocket: WebSocket) -> Optional[HttpError]:
        request = websocket.request
        for callback in self.auth_callbacks:
            try:
                if is_async_callable(callback) or getattr(callback, "is_async", False):
                    result = callback(request)
                    if inspect.isawaitable(result):
                        result = await result
                else:
                    # sync callbacks may hit the database (tokens, sessions...)
                    result = await sync_to_async(callback)(request)
            except HttpError as e:
                return e
            if result:
                request.auth = result  # type: ignore[attr-defined]
                websocket.auth = result
                return None
        return AuthenticationError()

    async def run(self, websocket: WebSocket, path_params: Dict[str, Any]) -> None:
        request = websocket.request
        websocket.path_params = path_params

        if self.auth_callbacks:
            # Cookies are sent by browsers on cross-site websocket handshakes and
            # Django's CSRF check does not protect GET requests, so cookie based
            # auth is protected by validating the Origin header instead.
            request._ninja_csrf_exempt = True  # type: ignore[attr-defined]
            if self._requires_origin_check() and not origin_is_allowed(request):
                await deny(websocket, 403, "Origin not allowed")
                return
            error = await self._authenticate(websocket)
            if error is not None:
                await deny(websocket, error.status_code, error.message)
                return

        try:
            values = self._get_values(request, path_params)
        except ValidationError as e:
            await deny(websocket, 422, e.errors)
            return

        values[cast(str, self.signature.websocket_arg)] = websocket
        if self._pass_request:
            values["request"] = request
        await self.view_func(**values)
