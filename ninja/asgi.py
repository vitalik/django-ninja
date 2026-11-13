"""
ASGI entry point that adds websocket support to a Django project.

Django's own ASGI handler only speaks HTTP, so websocket connections are
routed here instead::

    # asgi.py
    import os

    from ninja.asgi import get_asgi_application

    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "mysite.settings")
    application = get_asgi_application()

HTTP (and lifespan) traffic is forwarded untouched to Django. Websocket
connections are resolved against the project's URLconf, where every
``@api.websocket(...)`` route is registered alongside the HTTP ones.

``NinjaASGI()`` without an inner app only handles websockets, which allows
plugging it into other ASGI routers (e.g. ``channels.routing.ProtocolTypeRouter``).
"""

import asyncio
import logging
from typing import Any, Dict, Optional, Tuple

from asgiref.sync import sync_to_async
from django.conf import settings
from django.core import signals
from django.core.exceptions import DisallowedHost
from django.urls import Resolver404, resolve, set_script_prefix

from ninja.errors import HttpError
from ninja.websockets.connection import WebSocket
from ninja.websockets.handshake import deny, reject, truncate_reason
from ninja.websockets.operation import WebSocketOperation
from ninja.websockets.types import (
    Receive,
    Scope,
    Send,
    WebSocketClose,
    WebSocketDisconnect,
    WebSocketException,
    WebSocketState,
)

__all__ = ["NinjaASGI", "get_asgi_application"]

logger = logging.getLogger("ninja.websockets")

ASGIApp = Any


def get_asgi_application() -> "NinjaASGI":
    """Drop-in replacement for ``django.core.asgi.get_asgi_application``."""
    from django.core.asgi import get_asgi_application as get_django_application

    return NinjaASGI(get_django_application())


class NinjaASGI:
    """
    Args:
        app: ASGI application for non-websocket scopes (usually Django's).
        urlconf: URLconf used to resolve websocket paths (default ROOT_URLCONF).
    """

    # Overridden by ninja.testing: re-raise handler errors so they surface in
    # tests (it also replaces the request signals of the handshake).
    _raise_exceptions = False

    def __init__(self, app: Optional[ASGIApp] = None, *, urlconf: Any = None):
        self.app = app
        self.urlconf = urlconf

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] == "websocket":
            await self.handle_websocket(scope, receive, send)
            return
        if self.app is None:
            raise RuntimeError(
                f"NinjaASGI was created without an inner application and cannot "
                f"handle {scope['type']!r} connections"
            )
        await self.app(scope, receive, send)

    def get_urlconf(self, websocket: WebSocket) -> Any:
        """
        The URLconf used to resolve this connection (None = ROOT_URLCONF).

        Override it when the URLconf depends on the request, as middlewares
        like django-hosts or django-tenants do for HTTP (they don't run for
        websockets)::

            class HostsASGI(NinjaASGI):
                def get_urlconf(self, websocket):
                    host = websocket.request.get_host().split(":")[0]
                    return "myproject.urls_api" if host.startswith("api.") else None
        """
        return self.urlconf

    def resolve_operation(
        self, websocket: WebSocket
    ) -> Tuple[Optional[WebSocketOperation], Dict[str, Any]]:
        try:
            match = resolve(websocket.request.path_info, self.get_urlconf(websocket))
        except Resolver404:
            return None, {}
        operation = getattr(match.func, "ninja_websocket_operation", None)
        return operation, match.kwargs

    async def handle_websocket(
        self, scope: Scope, receive: Receive, send: Send
    ) -> None:
        set_script_prefix(_get_script_prefix(scope))
        websocket = WebSocket(scope, receive, send)
        operation: Optional[WebSocketOperation] = None
        values: Optional[Dict[str, Any]] = None
        try:
            # The handshake is processed like a Django request: its sync code
            # (signals, auth callbacks, throttles) runs in a thread of its own and
            # request_finished closes the database connections it opened. That
            # thread is released before the handler runs, so long-lived
            # connections don't keep one each (sync code in handlers uses the
            # thread shared by code outside requests, as with Channels).
            async with _thread_sensitive_context():
                await self._handshake_started(scope)
                try:
                    if await _check_host(websocket):
                        operation, path_params = self.resolve_operation(websocket)
                        if operation is None:
                            await deny(websocket, 404, "Not Found")
                        else:
                            values = await operation.handshake(websocket, path_params)
                finally:
                    await self._handshake_finished()
            if operation is None or values is None:
                return  # rejected
            await operation.view_func(**values)
            await _close(websocket, WebSocketClose.NORMAL_CLOSURE)
        except WebSocketDisconnect:
            pass
        except WebSocketException as e:
            await _close(websocket, e.code, truncate_reason(e.reason))
        except asyncio.CancelledError:
            raise  # server shutdown (an Exception subclass on Python 3.7)
        except Exception as exc:
            if operation is None:
                raise  # not raised by user code (host check, URL resolution)
            # API exception handlers apply like for HTTP (e.g. HttpError(404)
            # before accept() becomes a 404 response, after it a 1008 close)
            response = operation.response_for_exception(websocket.request, exc)
            # unexpected errors only: not HttpError(503) raised on purpose
            if response is None or (
                response.status_code >= 500 and not isinstance(exc, HttpError)
            ):
                await self._report_error(websocket)
            if response is not None:
                await reject(websocket, response)
                return
            await _close(websocket, WebSocketClose.INTERNAL_ERROR)
            if self._raise_exceptions:
                raise

    async def _handshake_started(self, scope: Scope) -> None:
        await sync_to_async(signals.request_started.send, thread_sensitive=True)(
            sender=self.__class__, scope=scope
        )

    async def _handshake_finished(self) -> None:
        # closes the database connections opened during the handshake
        await sync_to_async(signals.request_finished.send, thread_sensitive=True)(
            sender=self.__class__
        )

    async def _report_error(self, websocket: WebSocket) -> None:
        logger.exception("Error in websocket handler for %s", websocket.path)
        # error reporting tools (Sentry, Rollbar...) listen to this signal;
        # sync_to_async keeps sys.exc_info() available to receivers
        await sync_to_async(signals.got_request_exception.send, thread_sensitive=True)(
            sender=None, request=websocket.request
        )


class _NoContext:  # pragma: no cover - asgiref < 3.3 (Django 3.1)
    async def __aenter__(self) -> None:
        return None

    async def __aexit__(self, *exc_info: Any) -> None:
        return None


def _thread_sensitive_context() -> Any:
    try:
        from asgiref.sync import ThreadSensitiveContext
    except ImportError:  # pragma: no cover - asgiref < 3.3 (Django 3.1)
        return _NoContext()
    return ThreadSensitiveContext()  # type: ignore[no-untyped-call]


async def _check_host(websocket: WebSocket) -> bool:
    """Validate the Host header against ALLOWED_HOSTS, like Django does for HTTP."""
    try:
        websocket.request.get_host()
    except DisallowedHost as e:
        logging.getLogger("django.security.DisallowedHost").error(str(e))
        await deny(websocket, 400, "Invalid Host header")
        return False
    return True


def _get_script_prefix(scope: Scope) -> str:
    # same logic as Django's ASGI handler (kept here for Django < 5.0 support)
    if settings.FORCE_SCRIPT_NAME:
        return str(settings.FORCE_SCRIPT_NAME)
    return str(scope.get("root_path", "") or "")


async def _close(websocket: WebSocket, code: int, reason: str = "") -> None:
    """Close the connection unless the handler or the client already did it."""
    if websocket.client_state == WebSocketState.DISCONNECTED:
        # nothing may be sent once the client is gone (ASGI spec); some
        # servers raise, e.g. uvicorn's "websockets" implementation
        return
    if websocket.application_state not in {
        WebSocketState.CONNECTING,
        WebSocketState.CONNECTED,
    }:
        return
    try:
        await websocket.close(code=code, reason=reason)
    except WebSocketDisconnect:
        pass
