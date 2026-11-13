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

import logging
from typing import Any, Dict, Optional, Tuple

from asgiref.sync import sync_to_async
from django.conf import settings
from django.core import signals
from django.urls import Resolver404, resolve, set_script_prefix

from ninja.websockets.connection import WebSocket
from ninja.websockets.operation import WebSocketOperation
from ninja.websockets.types import (
    Receive,
    Scope,
    Send,
    WebSocketClose,
    WebSocketDisconnect,
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
        raise_exceptions: re-raise handler errors after closing with 1011
            (used by the test client so failures surface in tests).
        send_signals: send Django's request_started/request_finished signals
            (they close stale database connections, like for HTTP requests).
    """

    def __init__(
        self,
        app: Optional[ASGIApp] = None,
        *,
        urlconf: Any = None,
        raise_exceptions: bool = False,
        send_signals: bool = True,
    ):
        self.app = app
        self.urlconf = urlconf
        self.raise_exceptions = raise_exceptions
        self.send_signals = send_signals

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

    def resolve_operation(
        self, websocket: WebSocket
    ) -> Tuple[Optional[WebSocketOperation], Dict[str, Any]]:
        try:
            match = resolve(websocket.request.path_info, self.urlconf)
        except Resolver404:
            return None, {}
        operation = getattr(match.func, "ninja_websocket_operation", None)
        return operation, match.kwargs

    async def handle_websocket(
        self, scope: Scope, receive: Receive, send: Send
    ) -> None:
        set_script_prefix(_get_script_prefix(scope))
        if self.send_signals:
            await sync_to_async(signals.request_started.send, thread_sensitive=True)(
                sender=self.__class__, scope=scope
            )
        websocket = WebSocket(scope, receive, send)
        try:
            operation, path_params = self.resolve_operation(websocket)
            if operation is None:
                await _close(websocket, WebSocketClose.POLICY_VIOLATION, "Not Found")
                return
            try:
                await operation.run(websocket, path_params)
            except WebSocketDisconnect:
                pass
            except Exception:
                logger.exception("Error in websocket handler for %s", websocket.path)
                await _close(websocket, WebSocketClose.INTERNAL_ERROR)
                if self.raise_exceptions:
                    raise
            else:
                await _close(websocket, WebSocketClose.NORMAL_CLOSURE)
        finally:
            if self.send_signals:
                await sync_to_async(
                    signals.request_finished.send, thread_sensitive=True
                )(sender=self.__class__)


def _get_script_prefix(scope: Scope) -> str:
    # same logic as Django's ASGI handler (kept here for Django < 5.0 support)
    if settings.FORCE_SCRIPT_NAME:
        return str(settings.FORCE_SCRIPT_NAME)
    return str(scope.get("root_path", "") or "")


async def _close(websocket: WebSocket, code: int, reason: str = "") -> None:
    """Close the connection unless the handler already did it."""
    if websocket.application_state not in {
        WebSocketState.CONNECTING,
        WebSocketState.CONNECTED,
    }:
        return
    try:
        await websocket.close(code=code, reason=reason)
    except WebSocketDisconnect:
        pass
