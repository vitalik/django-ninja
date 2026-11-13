"""
WebSocket support for Django Ninja, with no third-party dependencies.

Endpoints are registered with ``@api.websocket(path)`` / ``@router.websocket(path)``
and served by the ASGI application from :mod:`ninja.asgi`.
"""

from ninja.websockets.connection import WebSocket
from ninja.websockets.types import (
    WebSocketClose,
    WebSocketDisconnect,
    WebSocketException,
    WebSocketState,
)

__all__ = [
    "WebSocket",
    "WebSocketDisconnect",
    "WebSocketException",
    "WebSocketState",
    "WebSocketClose",
]
