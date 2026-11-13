from typing import TYPE_CHECKING, Any, Callable, Dict, List, Optional, Sequence, cast

import pydantic
from django.http import HttpRequest, HttpResponse, JsonResponse

from ninja.constants import NOT_SET
from ninja.errors import ConfigError, ValidationErrorContext
from ninja.signature import ViewSignature, is_async
from ninja.types import DictStrAny
from ninja.websockets import WebSocket, WebSocketClose

if TYPE_CHECKING:
    from ninja import NinjaAPI  # pragma: no cover

__all__ = ["WebSocketOperation"]

_ALLOWED_PARAM_SOURCES = {"path", "query", "header", "cookie"}

UPGRADE_NOT_HANDLED_DETAIL = (
    "WebSocket upgrade requests cannot be handled by Django's HTTP handler. "
    "Run an ASGI server (uvicorn, daphne, hypercorn...) and serve "
    "'ninja.asgi.get_asgi_application()' from your asgi.py. "
    "WSGI servers do not support WebSockets."
)


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
            detail = "This endpoint only accepts WebSocket connections."
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

    async def run(self, websocket: WebSocket, path_params: Dict[str, Any]) -> None:
        from ninja.errors import ValidationError

        request = websocket.request
        websocket.path_params = path_params
        try:
            values = self._get_values(request, path_params)
        except ValidationError as e:
            await websocket.close(
                code=WebSocketClose.POLICY_VIOLATION,
                reason=_truncate_reason(str(e.errors)),
            )
            return

        values[cast(str, self.signature.websocket_arg)] = websocket
        if self._pass_request:
            values["request"] = request
        await self.view_func(**values)


def _truncate_reason(reason: str) -> str:
    # Close frame payload is limited to 125 bytes (2 of them for the code)
    encoded = reason.encode("utf-8")
    if len(encoded) <= 123:
        return reason
    return encoded[:120].decode("utf-8", errors="ignore") + "..."
