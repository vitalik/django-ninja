"""
In-memory websocket test sessions (no server, no third-party dependencies).

    client = TestClient(api)
    with client.websocket_connect("/ws?token=1") as ws:
        ws.send_json({"hello": "world"})
        assert ws.receive_json() == {...}

    client = TestAsyncClient(api)
    async with client.websocket_connect("/ws") as ws:
        await ws.send_text("hi")
        assert await ws.receive_text() == "hi"
"""

import asyncio
import json
import threading
from typing import Any, Coroutine, Dict, List, Optional, Tuple, TypeVar

from ninja.asgi import NinjaASGI
from ninja.responses import NinjaJSONEncoder
from ninja.websockets.types import (
    Message,
    Scope,
    WebSocketClose,
    WebSocketDisconnect,
)

__all__ = [
    "WebSocketDenied",
    "AsyncWebSocketTestSession",
    "WebSocketTestSession",
    "build_websocket_scope",
]

T = TypeVar("T")
_APP_FINISHED = "ninja.testing.app_finished"


class TestNinjaASGI(NinjaASGI):
    """NinjaASGI for tests: handler errors are re-raised, no request signals."""

    __test__ = False  # not a pytest test class
    _raise_exceptions = True
    _send_signals = False


class WebSocketDenied(Exception):
    """The handshake was rejected with an HTTP response (e.g. 401 from auth)."""

    def __init__(
        self, status_code: int, headers: List[Tuple[bytes, bytes]], body: bytes
    ):
        self.status_code = status_code
        self.headers = headers
        self.body = body
        super().__init__(status_code, body)

    def json(self) -> Any:
        return json.loads(self.body)


def build_websocket_scope(
    path: str,
    headers: Optional[Dict[str, str]] = None,
    subprotocols: Optional[List[str]] = None,
) -> Scope:
    path, _, query = path.partition("?")
    raw_headers = [(b"host", b"testserver")]
    for name, value in (headers or {}).items():
        raw_headers.append((name.lower().encode("latin-1"), value.encode("latin-1")))
    if subprotocols:
        # real servers expose the requested subprotocols both ways
        raw_headers.append((
            b"sec-websocket-protocol",
            ", ".join(subprotocols).encode(),
        ))
    return {
        "type": "websocket",
        "asgi": {"version": "3.0"},
        "http_version": "1.1",
        "scheme": "ws",
        "path": path,
        "raw_path": path.encode(),
        "root_path": "",
        "query_string": query.encode(),
        "headers": raw_headers,
        "client": ["testclient", 50000],
        "server": ["testserver", 80],
        "subprotocols": list(subprotocols or []),
        "extensions": {"websocket.http.response": {}},
    }


class AsyncWebSocketTestSession:
    """Drives an ASGI app through a websocket connection, in the same event loop."""

    def __init__(self, app: Any, scope: Scope, timeout: Optional[float] = 10) -> None:
        self.app = app
        self.scope = scope
        self.timeout = timeout
        self.accepted_subprotocol: Optional[str] = None
        self.accepted_headers: List[Tuple[bytes, bytes]] = []
        self._to_app: Optional[asyncio.Queue[Message]] = None
        self._from_app: Optional[asyncio.Queue[Message]] = None
        self._task: Optional[asyncio.Future[None]] = None
        self._error: Optional[BaseException] = None

    # connection lifecycle ----------------------------------------------------

    async def __aenter__(self) -> "AsyncWebSocketTestSession":
        self._to_app = asyncio.Queue()
        self._from_app = asyncio.Queue()
        self._task = asyncio.ensure_future(self._run_app())
        await self._to_app.put({"type": "websocket.connect"})

        message = await self._next_message()
        if message["type"] == "websocket.http.response.start":
            body = b""
            while True:
                chunk = await self._next_message()
                body += chunk.get("body", b"")
                if not chunk.get("more_body", False):
                    break
            await self._wait_app()
            raise WebSocketDenied(message["status"], message.get("headers", []), body)
        if message["type"] == "websocket.close":
            await self._wait_app()
            raise WebSocketDisconnect(message.get("code", 1000), message.get("reason"))
        assert message["type"] == "websocket.accept", message
        self.accepted_subprotocol = message.get("subprotocol")
        self.accepted_headers = list(message.get("headers") or [])
        return self

    async def __aexit__(self, *exc_info: Any) -> None:
        if self._task is not None and not self._task.done():
            await self.close()
        await self._wait_app()

    async def _run_app(self) -> None:
        assert self._from_app is not None
        try:
            await self.app(self.scope, self._app_receive, self._app_send)
        except BaseException as e:  # noqa: B036 - re-raised in the test
            self._error = e
        finally:
            await self._from_app.put({"type": _APP_FINISHED})

    async def _app_receive(self) -> Message:
        assert self._to_app is not None
        return await self._to_app.get()

    async def _app_send(self, message: Message) -> None:
        assert self._from_app is not None
        await self._from_app.put(message)

    async def _wait_app(self) -> None:
        assert self._task is not None
        await asyncio.wait_for(asyncio.shield(self._task), self.timeout)
        self._raise_app_error()

    def _raise_app_error(self) -> None:
        if self._error is not None:
            error, self._error = self._error, None
            raise error

    async def _next_message(self) -> Message:
        assert self._from_app is not None
        message = await asyncio.wait_for(self._from_app.get(), self.timeout)
        if message["type"] == _APP_FINISHED:
            self._raise_app_error()
            raise RuntimeError("The websocket application finished without closing")
        return message

    # client API --------------------------------------------------------------

    async def send(self, message: Message) -> None:
        assert self._to_app is not None
        await self._to_app.put(message)

    async def send_text(self, data: str) -> None:
        await self.send({"type": "websocket.receive", "text": data})

    async def send_bytes(self, data: bytes) -> None:
        await self.send({"type": "websocket.receive", "bytes": data})

    async def send_json(self, data: Any, mode: str = "text") -> None:
        text = json.dumps(data, cls=NinjaJSONEncoder)
        if mode == "text":
            await self.send_text(text)
        else:
            await self.send_bytes(text.encode("utf-8"))

    async def close(self, code: int = WebSocketClose.NORMAL_CLOSURE) -> None:
        await self.send({"type": "websocket.disconnect", "code": code})

    async def receive(self) -> Message:
        message = await self._next_message()
        if message["type"] == "websocket.close":
            raise WebSocketDisconnect(message.get("code", 1000), message.get("reason"))
        return message

    async def receive_text(self) -> str:
        return str((await self.receive())["text"])

    async def receive_bytes(self) -> bytes:
        return bytes((await self.receive())["bytes"])

    async def receive_json(self, mode: str = "text") -> Any:
        message = await self.receive()
        if mode == "text":
            return json.loads(message["text"])
        return json.loads(message["bytes"].decode("utf-8"))


class WebSocketTestSession:
    """Synchronous facade running an AsyncWebSocketTestSession in a loop thread."""

    def __init__(self, app: Any, scope: Scope, timeout: Optional[float] = 10) -> None:
        self._session = AsyncWebSocketTestSession(app, scope, timeout)
        self._loop: Optional[asyncio.AbstractEventLoop] = None
        self._thread: Optional[threading.Thread] = None

    @property
    def accepted_subprotocol(self) -> Optional[str]:
        return self._session.accepted_subprotocol

    @property
    def accepted_headers(self) -> List[Tuple[bytes, bytes]]:
        return self._session.accepted_headers

    def _call(self, coro: Coroutine[Any, Any, T]) -> T:
        assert self._loop is not None
        return asyncio.run_coroutine_threadsafe(coro, self._loop).result()

    def _stop_loop(self) -> None:
        assert self._loop is not None and self._thread is not None
        self._loop.call_soon_threadsafe(self._loop.stop)
        self._thread.join()
        self._loop.close()

    def __enter__(self) -> "WebSocketTestSession":
        self._loop = asyncio.new_event_loop()
        self._thread = threading.Thread(target=self._loop.run_forever, daemon=True)
        self._thread.start()
        try:
            self._call(self._session.__aenter__())
        except BaseException:
            self._stop_loop()
            raise
        return self

    def __exit__(self, *exc_info: Any) -> None:
        try:
            self._call(self._session.__aexit__(*exc_info))
        finally:
            self._stop_loop()

    def send(self, message: Message) -> None:
        self._call(self._session.send(message))

    def send_text(self, data: str) -> None:
        self._call(self._session.send_text(data))

    def send_bytes(self, data: bytes) -> None:
        self._call(self._session.send_bytes(data))

    def send_json(self, data: Any, mode: str = "text") -> None:
        self._call(self._session.send_json(data, mode))

    def close(self, code: int = WebSocketClose.NORMAL_CLOSURE) -> None:
        self._call(self._session.close(code))

    def receive(self) -> Message:
        return self._call(self._session.receive())

    def receive_text(self) -> str:
        return self._call(self._session.receive_text())

    def receive_bytes(self) -> bytes:
        return self._call(self._session.receive_bytes())

    def receive_json(self, mode: str = "text") -> Any:
        return self._call(self._session.receive_json(mode))
