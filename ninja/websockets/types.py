import enum
from typing import Any, Awaitable, Callable, MutableMapping, Optional

__all__ = [
    "Scope",
    "Message",
    "Receive",
    "Send",
    "WebSocketClose",
    "WebSocketState",
    "WebSocketDisconnect",
    "WebSocketException",
]

Scope = MutableMapping[str, Any]
Message = MutableMapping[str, Any]
Receive = Callable[[], Awaitable[Message]]
Send = Callable[[Message], Awaitable[None]]


class WebSocketClose(enum.IntEnum):
    """Common close codes (RFC 6455, section 7.4.1)."""

    NORMAL_CLOSURE = 1000
    GOING_AWAY = 1001
    PROTOCOL_ERROR = 1002
    UNSUPPORTED_DATA = 1003
    NO_STATUS_RECEIVED = 1005
    ABNORMAL_CLOSURE = 1006
    INVALID_PAYLOAD = 1007
    POLICY_VIOLATION = 1008
    MESSAGE_TOO_BIG = 1009
    MANDATORY_EXTENSION = 1010
    INTERNAL_ERROR = 1011


class WebSocketState(enum.Enum):
    CONNECTING = 0
    CONNECTED = 1
    DISCONNECTED = 2
    RESPONSE = 3


class WebSocketDisconnect(Exception):
    """Raised when the client disconnects (or the connection is lost)."""

    def __init__(
        self, code: int = WebSocketClose.NORMAL_CLOSURE, reason: Optional[str] = None
    ) -> None:
        self.code = code
        self.reason = reason or ""
        super().__init__(code, self.reason)


class WebSocketException(Exception):
    """
    Raise it from a handler or an auth callback to close the connection with
    the given code (before ``accept()`` the handshake is rejected)::

        raise WebSocketException(code=WebSocketClose.POLICY_VIOLATION, reason="...")
    """

    def __init__(self, code: int, reason: Optional[str] = None) -> None:
        self.code = code
        self.reason = reason or ""
        super().__init__(code, self.reason)
