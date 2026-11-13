"""Helpers used while a websocket handshake is being processed."""

import json
from typing import Any, List, Tuple
from urllib.parse import urlsplit

from django.conf import settings
from django.core.exceptions import DisallowedHost
from django.http import HttpRequest, JsonResponse
from django.http.response import HttpResponseBase
from django.utils.http import is_same_domain

from ninja.websockets.connection import WebSocket
from ninja.websockets.types import WebSocketClose, WebSocketState

__all__ = ["origin_is_allowed", "deny", "reject", "UPGRADE_NOT_HANDLED_DETAIL"]

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
    """Reject with a ``{"detail": ...}`` JSON response (see :func:`reject`)."""
    await reject(websocket, JsonResponse({"detail": detail}, status=status_code))


async def reject(websocket: WebSocket, response: HttpResponseBase) -> None:
    """
    Turn an HTTP response (usually built by the API exception handlers) into
    the end of a websocket connection.

    Before ``accept()``, if the server supports the "websocket.http.response"
    ASGI extension, the response itself is sent (status, headers, cookies and
    body). Otherwise the connection is closed with a code derived from the
    status (429 -> 1013, 5xx -> 1011, else 1008) and the error detail as reason.
    """
    state = websocket.application_state
    if state == WebSocketState.CONNECTING and _supports_http_response(websocket):
        await websocket.send({
            "type": "websocket.http.response.start",
            "status": response.status_code,
            "headers": _response_headers(response),
        })
        await websocket.send({
            "type": "websocket.http.response.body",
            "body": getattr(response, "content", b""),
        })
        return
    if state not in {WebSocketState.CONNECTING, WebSocketState.CONNECTED}:
        return
    await websocket.close(
        code=close_code_for_status(response.status_code),
        reason=truncate_reason(_close_reason(response)),
    )


def close_code_for_status(status_code: int) -> int:
    if status_code == 429:
        return WebSocketClose.TRY_AGAIN_LATER
    if status_code >= 500:
        return WebSocketClose.INTERNAL_ERROR
    return WebSocketClose.POLICY_VIOLATION


def _supports_http_response(websocket: WebSocket) -> bool:
    return "websocket.http.response" in (websocket.scope.get("extensions") or {})


def _response_headers(response: HttpResponseBase) -> List[Tuple[bytes, bytes]]:
    headers = [
        (name.lower().encode("latin-1"), value.encode("latin-1"))
        for name, value in response.items()
    ]
    for cookie in response.cookies.values():
        headers.append((b"set-cookie", cookie.output(header="").strip().encode()))
    return headers


def _close_reason(response: HttpResponseBase) -> str:
    """The "detail" of a JSON error body, or the HTTP reason phrase."""
    try:
        detail = json.loads(getattr(response, "content", b""))["detail"]
    except (ValueError, TypeError, KeyError):
        detail = None
    return detail if isinstance(detail, str) else response.reason_phrase


def truncate_reason(reason: str) -> str:
    # Close frame payload is limited to 125 bytes (2 of them for the code)
    encoded = reason.encode("utf-8")
    if len(encoded) <= 123:
        return reason
    return encoded[:120].decode("utf-8", errors="ignore") + "..."
