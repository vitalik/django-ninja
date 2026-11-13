"""
The WebSocket connection, implemented directly on top of the ASGI protocol.

No third-party dependencies are required: the ASGI websocket protocol is just
an exchange of dictionaries between the server and the application
(see https://asgi.readthedocs.io/en/latest/specs/www.html#websocket).
"""

import json
from typing import (
    Any,
    AsyncIterator,
    Dict,
    Iterable,
    List,
    Mapping,
    Optional,
    Tuple,
    Type,
    TypeVar,
    overload,
)

from django.http import HttpRequest, QueryDict

from ninja.responses import NinjaJSONEncoder
from ninja.websockets.request import build_handshake_request
from ninja.websockets.schemas import type_adapter
from ninja.websockets.types import (
    Message,
    Receive,
    Scope,
    Send,
    WebSocketClose,
    WebSocketDisconnect,
    WebSocketState,
)

__all__ = ["WebSocket"]

T = TypeVar("T")


class WebSocket:
    """
    A WebSocket connection, with an API modeled after FastAPI/Starlette:

        await websocket.accept()
        data = await websocket.receive_json()
        await websocket.send_json({"echo": data})
        await websocket.close()
    """

    json_encoder = NinjaJSONEncoder

    def __init__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope.get("type") != "websocket":
            raise ValueError("WebSocket requires an ASGI scope of type 'websocket'")
        self.scope = scope
        self._receive = receive
        self._send = send
        self.client_state = WebSocketState.CONNECTING
        self.application_state = WebSocketState.CONNECTING
        self.path_params: Dict[str, Any] = {}
        self.auth: Any = None
        self._request: Optional[HttpRequest] = None

    # Connection details ------------------------------------------------------

    @property
    def path(self) -> str:
        return str(self.scope.get("path", ""))

    @property
    def query_params(self) -> QueryDict:
        """Same as ``websocket.request.GET``."""
        return self.request.GET

    @property
    def headers(self) -> Mapping[str, str]:
        """Same as ``websocket.request.headers`` (case-insensitive)."""
        return self.request.headers

    @property
    def cookies(self) -> Dict[str, str]:
        """Same as ``websocket.request.COOKIES``."""
        return self.request.COOKIES

    @property
    def client(self) -> Optional[Tuple[str, int]]:
        client = self.scope.get("client")
        return tuple(client) if client else None

    @property
    def subprotocols(self) -> List[str]:
        return list(self.scope.get("subprotocols", []))

    @property
    def request(self) -> HttpRequest:
        """
        A read-only Django request built from the handshake (method GET, no body).

        It is what auth callbacks and Query/Header/Cookie/Path params receive,
        so existing ninja security classes work unchanged for websockets.
        """
        if self._request is None:
            self._request = build_handshake_request(self.scope)
        return self._request

    # Low level ASGI messages -------------------------------------------------

    async def receive(self) -> Message:
        """Receive a raw ASGI message, keeping track of the client state."""
        if self.client_state == WebSocketState.CONNECTING:
            message = await self._receive()
            if message["type"] != "websocket.connect":
                raise RuntimeError(
                    'Expected ASGI message "websocket.connect", '
                    f"but got {message['type']!r}"
                )
            self.client_state = WebSocketState.CONNECTED
            return message

        if self.client_state == WebSocketState.CONNECTED:
            message = await self._receive()
            if message["type"] not in {"websocket.receive", "websocket.disconnect"}:
                raise RuntimeError(
                    'Expected ASGI message "websocket.receive" or '
                    f'"websocket.disconnect", but got {message["type"]!r}'
                )
            if message["type"] == "websocket.disconnect":
                self.client_state = WebSocketState.DISCONNECTED
            return message

        raise RuntimeError(
            'Cannot call "receive" once a disconnect message has been received.'
        )

    async def send(self, message: Message) -> None:
        """Send a raw ASGI message, keeping track of the application state."""
        message_type = message["type"]

        if self.application_state == WebSocketState.CONNECTING:
            allowed = {
                "websocket.accept",
                "websocket.close",
                "websocket.http.response.start",
            }
            if message_type not in allowed:
                raise RuntimeError(
                    f"Expected one of {sorted(allowed)}, but got {message_type!r}"
                )
            if message_type == "websocket.accept":
                self.application_state = WebSocketState.CONNECTED
            elif message_type == "websocket.close":
                self.application_state = WebSocketState.DISCONNECTED
            else:
                self.application_state = WebSocketState.RESPONSE
            await self._send(message)
            return

        if self.application_state == WebSocketState.CONNECTED:
            if message_type not in {"websocket.send", "websocket.close"}:
                raise RuntimeError(
                    'Expected ASGI message "websocket.send" or "websocket.close", '
                    f"but got {message_type!r}"
                )
            if message_type == "websocket.close":
                self.application_state = WebSocketState.DISCONNECTED
            try:
                await self._send(message)
            except OSError as e:
                self.application_state = WebSocketState.DISCONNECTED
                raise WebSocketDisconnect(WebSocketClose.ABNORMAL_CLOSURE) from e
            return

        if self.application_state == WebSocketState.RESPONSE:
            if message_type != "websocket.http.response.body":
                raise RuntimeError(
                    'Expected ASGI message "websocket.http.response.body", '
                    f"but got {message_type!r}"
                )
            if not message.get("more_body", False):
                self.application_state = WebSocketState.DISCONNECTED
            await self._send(message)
            return

        raise RuntimeError('Cannot call "send" once a close message has been sent.')

    # High level API ----------------------------------------------------------

    async def accept(
        self,
        subprotocol: Optional[str] = None,
        headers: Optional[Iterable[Tuple[bytes, bytes]]] = None,
    ) -> None:
        if self.client_state == WebSocketState.CONNECTING:
            # wait for the "websocket.connect" message
            await self.receive()
        await self.send({
            "type": "websocket.accept",
            "subprotocol": subprotocol,
            "headers": list(headers or []),
        })

    async def close(
        self, code: int = WebSocketClose.NORMAL_CLOSURE, reason: Optional[str] = None
    ) -> None:
        await self.send({
            "type": "websocket.close",
            "code": int(code),
            "reason": reason or "",
        })

    def _check_connected(self) -> None:
        if self.application_state != WebSocketState.CONNECTED:
            raise RuntimeError(
                'WebSocket is not connected. Need to call "accept" first.'
            )

    async def _receive_data(self) -> Message:
        self._check_connected()
        message = await self.receive()
        if message["type"] == "websocket.disconnect":
            raise WebSocketDisconnect(
                message.get("code", WebSocketClose.NORMAL_CLOSURE),
                message.get("reason"),
            )
        return message

    async def receive_text(self) -> str:
        message = await self._receive_data()
        text = message.get("text")
        if text is None:
            raise TypeError("Expected a text frame but received a binary frame")
        return str(text)

    async def receive_bytes(self) -> bytes:
        message = await self._receive_data()
        data = message.get("bytes")
        if data is None:
            raise TypeError("Expected a binary frame but received a text frame")
        return bytes(data)

    @overload
    async def receive_json(self, mode: str = ..., *, schema: None = ...) -> Any: ...

    @overload
    async def receive_json(self, mode: str = ..., *, schema: Type[T]) -> T: ...

    @overload
    async def receive_json(self, mode: str = ..., *, schema: Any) -> Any: ...

    async def receive_json(self, mode: str = "text", *, schema: Any = None) -> Any:
        """
        Receive a JSON message. With ``schema`` (a pydantic model or any type
        such as ``List[Item]``) the data is validated and converted, raising
        ``pydantic.ValidationError`` when it does not match.
        """
        if mode not in {"text", "binary"}:
            raise ValueError('The "mode" argument should be "text" or "binary".')
        if mode == "text":
            data = json.loads(await self.receive_text())
        else:
            data = json.loads((await self.receive_bytes()).decode("utf-8"))
        if schema is not None:
            return type_adapter(schema).validate_python(data)
        return data

    async def send_text(self, data: str) -> None:
        await self.send({"type": "websocket.send", "text": data})

    async def send_bytes(self, data: bytes) -> None:
        await self.send({"type": "websocket.send", "bytes": data})

    async def send_json(
        self, data: Any, mode: str = "text", *, schema: Any = None
    ) -> None:
        """
        Send data as JSON. Pydantic models are serialized automatically; with
        ``schema`` the data (e.g. a Django model instance) is first validated
        against it, like the ``response=`` argument of HTTP operations.
        """
        if mode not in {"text", "binary"}:
            raise ValueError('The "mode" argument should be "text" or "binary".')
        if schema is not None:
            adapter = type_adapter(schema)
            data = adapter.dump_python(
                adapter.validate_python(data, from_attributes=True), mode="json"
            )
        text = json.dumps(
            data, cls=self.json_encoder, separators=(",", ":"), ensure_ascii=False
        )
        if mode == "text":
            await self.send_text(text)
        else:
            await self.send_bytes(text.encode("utf-8"))

    async def iter_text(self) -> AsyncIterator[str]:
        try:
            while True:
                yield await self.receive_text()
        except WebSocketDisconnect:
            pass

    async def iter_bytes(self) -> AsyncIterator[bytes]:
        try:
            while True:
                yield await self.receive_bytes()
        except WebSocketDisconnect:
            pass

    @overload
    def iter_json(
        self, mode: str = ..., *, schema: None = ...
    ) -> AsyncIterator[Any]: ...

    @overload
    def iter_json(self, mode: str = ..., *, schema: Type[T]) -> AsyncIterator[T]: ...

    @overload
    def iter_json(self, mode: str = ..., *, schema: Any) -> AsyncIterator[Any]: ...

    async def iter_json(
        self, mode: str = "text", *, schema: Any = None
    ) -> AsyncIterator[Any]:
        try:
            while True:
                yield await self.receive_json(mode, schema=schema)
        except WebSocketDisconnect:
            pass
