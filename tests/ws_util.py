"""Shared helpers for websocket tests (in-memory ASGI transport)."""

import asyncio
import itertools

from django.urls import path

CONNECT = {"type": "websocket.connect"}
HTTP_RESPONSE_EXTENSION = {"websocket.http.response": {}}

_namespaces = itertools.count()


def unique_namespace(prefix="ws"):
    """A urls_namespace that is unique for the whole test session."""
    return f"{prefix}-{next(_namespaces)}"


class UrlConf:
    """Hashable urlconf object (django caches one resolver per urlconf)."""

    def __init__(self, urlpatterns):
        self.urlpatterns = urlpatterns


def api_urlconf(api, prefix="api/"):
    return UrlConf([path(prefix, api.urls)])


class FakeTransport:
    """
    ASGI receive/send pair. Incoming messages are consumed in order; once
    exhausted the client "disconnects".
    """

    def __init__(self, incoming=None, send_error=None):
        self.incoming = [CONNECT] if incoming is None else list(incoming)
        self.sent = []
        self.send_error = send_error
        self.disconnected = False

    async def receive(self):
        await asyncio.sleep(0)
        message = (
            self.incoming.pop(0)
            if self.incoming
            else {"type": "websocket.disconnect", "code": 1000}
        )
        if message["type"] == "websocket.disconnect":
            self.disconnected = True
        return message

    async def send(self, message):
        if self.send_error:
            raise self.send_error
        if self.disconnected:
            # strict like uvicorn's "websockets" implementation: nothing may
            # be sent once the disconnect message was delivered
            if message["type"] == "websocket.close":
                raise RuntimeError("websocket.close sent after the client left")
            raise OSError("client disconnected")
        self.sent.append(message)

    @property
    def types(self):
        return [m["type"] for m in self.sent]


def make_scope(
    path="/ws", query=b"", headers=None, root_path="", extensions=None, host=True
):
    scope = {
        "type": "websocket",
        "path": path,
        "root_path": root_path,
        "query_string": query,
        "headers": ([(b"host", b"testserver")] if host else []) + list(headers or []),
        "scheme": "ws",
    }
    if extensions is not None:
        scope["extensions"] = extensions
    return scope


async def connect(app, path, incoming=None, send_error=None, **scope_kwargs):
    """Run a full websocket connection against an ASGI app; return the transport."""
    transport = FakeTransport(incoming, send_error)
    await app(make_scope(path, **scope_kwargs), transport.receive, transport.send)
    return transport
