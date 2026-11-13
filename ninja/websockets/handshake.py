"""Helpers used while a websocket handshake is being processed."""

import json
from typing import Any
from urllib.parse import urlsplit

from django.conf import settings
from django.core.exceptions import DisallowedHost
from django.http import HttpRequest
from django.utils.http import is_same_domain

from ninja.responses import NinjaJSONEncoder
from ninja.websockets.connection import WebSocket
from ninja.websockets.types import WebSocketClose

__all__ = ["origin_is_allowed", "deny", "UPGRADE_NOT_HANDLED_DETAIL"]

UPGRADE_NOT_HANDLED_DETAIL = (
    "WebSocket upgrade requests cannot be handled by Django's HTTP handler. "
    "Run an ASGI server (uvicorn, daphne, hypercorn...) and serve "
    "'ninja.asgi.get_asgi_application()' from your asgi.py. "
    "WSGI servers do not support WebSockets."
)
WEBSOCKET_ONLY_DETAIL = "This endpoint only accepts WebSocket connections."


def origin_is_allowed(request: HttpRequest) -> bool:
    """
    Same-origin check for websocket handshakes.

    Requests without an Origin header (non-browser clients) are allowed.
    Otherwise the origin host must match the request host (which is validated
    against ALLOWED_HOSTS) or be listed in settings.CSRF_TRUSTED_ORIGINS.
    """
    origin = request.headers.get("origin")
    if origin is None:
        return True
    parsed = urlsplit(origin)
    if not parsed.netloc:
        return False  # e.g. "null"
    try:
        if parsed.netloc == request.get_host():
            return True
    except DisallowedHost:
        return False
    for trusted in getattr(settings, "CSRF_TRUSTED_ORIGINS", []):
        if trusted in (origin, parsed.netloc):
            return True
        if "*" in trusted:
            scheme, _, pattern = trusted.rpartition("://")
            if (not scheme or scheme == parsed.scheme) and is_same_domain(
                parsed.netloc, pattern.replace("*", "", 1)
            ):
                return True
    return False


async def deny(websocket: WebSocket, status_code: int, detail: Any) -> None:
    """
    Reject a handshake.

    If the server supports the "websocket.http.response" ASGI extension, a
    regular HTTP response (e.g. 401 + JSON body) is sent. Otherwise the
    connection is closed with code 1008 (servers answer that with HTTP 403).
    """
    if "websocket.http.response" in (websocket.scope.get("extensions") or {}):
        body = json.dumps({"detail": detail}, cls=NinjaJSONEncoder).encode()
        await websocket.send({
            "type": "websocket.http.response.start",
            "status": status_code,
            "headers": [(b"content-type", b"application/json")],
        })
        await websocket.send({"type": "websocket.http.response.body", "body": body})
        return
    reason = (
        detail if isinstance(detail, str) else json.dumps(detail, cls=NinjaJSONEncoder)
    )
    await websocket.close(
        code=WebSocketClose.POLICY_VIOLATION, reason=truncate_reason(reason)
    )


def truncate_reason(reason: str) -> str:
    # Close frame payload is limited to 125 bytes (2 of them for the code)
    encoded = reason.encode("utf-8")
    if len(encoded) <= 123:
        return reason
    return encoded[:120].decode("utf-8", errors="ignore") + "..."
