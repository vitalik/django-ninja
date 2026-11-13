from datetime import date

import pytest
from ws_util import CONNECT, FakeTransport

from ninja import WebSocket, WebSocketDisconnect
from ninja.websockets import WebSocketClose, WebSocketState


def make_ws(incoming=None, scope=None, **kw):
    transport = FakeTransport(incoming, **kw)
    base_scope = {"type": "websocket", "path": "/ws"}
    base_scope.update(scope or {})
    return WebSocket(base_scope, transport.receive, transport.send), transport


DISCONNECT = {"type": "websocket.disconnect", "code": 1001, "reason": "bye"}


def text(value):
    return {"type": "websocket.receive", "text": value}


def binary(value):
    return {"type": "websocket.receive", "bytes": value}


def test_requires_websocket_scope():
    with pytest.raises(ValueError):
        WebSocket({"type": "http"}, None, None)


def test_connection_details():
    ws, _ = make_ws(
        scope={
            "query_string": b"a=1&a=2&b=x",
            "headers": [
                (b"Cookie", b"sessionid=abc; other=1"),
                (b"X-Multi", b"1"),
                (b"x-multi", b"2"),
            ],
            "client": ["127.0.0.1", 5000],
            "subprotocols": ["chat"],
        }
    )
    assert ws.path == "/ws"
    assert ws.query_params.getlist("a") == ["1", "2"]
    assert ws.query_params["b"] == "x"
    assert ws.query_params is ws.query_params  # cached
    assert ws.headers["x-multi"] == "1,2"
    assert ws.headers is ws.headers
    assert ws.cookies == {"sessionid": "abc", "other": "1"}
    assert ws.cookies is ws.cookies
    assert ws.client == ("127.0.0.1", 5000)
    assert ws.subprotocols == ["chat"]


def test_connection_details_defaults():
    ws, _ = make_ws()
    assert ws.client is None
    assert ws.subprotocols == []
    assert ws.headers == {}
    assert ws.cookies == {}
    assert len(ws.query_params) == 0


@pytest.mark.asyncio
async def test_echo_flow():
    ws, t = make_ws([
        CONNECT,
        text("hi"),
        binary(b"\x00\x01"),
        text('{"a": 1}'),
        binary(b'{"b": 2}'),
        DISCONNECT,
    ])
    await ws.accept(subprotocol="chat", headers=[(b"x-a", b"1")])
    assert ws.client_state == WebSocketState.CONNECTED
    assert ws.application_state == WebSocketState.CONNECTED

    assert await ws.receive_text() == "hi"
    assert await ws.receive_bytes() == b"\x00\x01"
    assert await ws.receive_json() == {"a": 1}
    assert await ws.receive_json(mode="binary") == {"b": 2}

    await ws.send_text("t")
    await ws.send_bytes(b"b")
    await ws.send_json({"d": date(2020, 1, 2), "ñ": 1})
    await ws.send_json([1], mode="binary")

    with pytest.raises(WebSocketDisconnect) as exc:
        await ws.receive_text()
    assert exc.value.code == 1001
    assert exc.value.reason == "bye"
    assert ws.client_state == WebSocketState.DISCONNECTED

    await ws.close()
    assert ws.application_state == WebSocketState.DISCONNECTED

    assert t.sent == [
        {
            "type": "websocket.accept",
            "subprotocol": "chat",
            "headers": [(b"x-a", b"1")],
        },
        {"type": "websocket.send", "text": "t"},
        {"type": "websocket.send", "bytes": b"b"},
        {"type": "websocket.send", "text": '{"d":"2020-01-02","ñ":1}'},
        {"type": "websocket.send", "bytes": b"[1]"},
        {"type": "websocket.close", "code": 1000, "reason": ""},
    ]


@pytest.mark.asyncio
async def test_accept_after_manual_connect_receive():
    ws, t = make_ws([CONNECT])
    assert await ws.receive() == CONNECT
    await ws.accept()
    assert t.sent[0]["type"] == "websocket.accept"


@pytest.mark.asyncio
async def test_iterators():
    ws, _ = make_ws([CONNECT, text("a"), text("b"), DISCONNECT])
    await ws.accept()
    assert [m async for m in ws.iter_text()] == ["a", "b"]

    ws, _ = make_ws([CONNECT, binary(b"a"), DISCONNECT])
    await ws.accept()
    assert [m async for m in ws.iter_bytes()] == [b"a"]

    ws, _ = make_ws([CONNECT, text("[1]"), {"type": "websocket.disconnect"}])
    await ws.accept()
    assert [m async for m in ws.iter_json()] == [[1]]


@pytest.mark.asyncio
async def test_disconnect_defaults():
    ws, _ = make_ws([CONNECT, {"type": "websocket.disconnect"}])
    await ws.accept()
    with pytest.raises(WebSocketDisconnect) as exc:
        await ws.receive_bytes()
    assert exc.value.code == WebSocketClose.NORMAL_CLOSURE
    assert exc.value.reason == ""


@pytest.mark.asyncio
async def test_frame_type_mismatch():
    ws, _ = make_ws([CONNECT, binary(b"x"), text("x")])
    await ws.accept()
    with pytest.raises(TypeError):
        await ws.receive_text()
    with pytest.raises(TypeError):
        await ws.receive_bytes()


@pytest.mark.asyncio
async def test_invalid_json_mode():
    ws, _ = make_ws([CONNECT])
    await ws.accept()
    with pytest.raises(ValueError):
        await ws.receive_json(mode="xml")
    with pytest.raises(ValueError):
        await ws.send_json({}, mode="xml")


@pytest.mark.asyncio
async def test_receive_before_accept():
    ws, _ = make_ws([CONNECT])
    with pytest.raises(RuntimeError, match="accept"):
        await ws.receive_text()


@pytest.mark.asyncio
async def test_receive_protocol_errors():
    ws, _ = make_ws([text("x")])
    with pytest.raises(RuntimeError, match="websocket.connect"):
        await ws.receive()

    ws, _ = make_ws([CONNECT, CONNECT])
    await ws.receive()
    with pytest.raises(RuntimeError, match="websocket.receive"):
        await ws.receive()

    ws, _ = make_ws([CONNECT, DISCONNECT])
    await ws.receive()
    await ws.receive()
    with pytest.raises(RuntimeError, match="disconnect"):
        await ws.receive()


@pytest.mark.asyncio
async def test_send_protocol_errors():
    ws, _ = make_ws()
    with pytest.raises(RuntimeError, match="Expected one of"):
        await ws.send_text("x")

    ws, _ = make_ws([CONNECT])
    await ws.accept()
    with pytest.raises(RuntimeError, match="websocket.send"):
        await ws.send({"type": "websocket.accept"})

    await ws.close(code=WebSocketClose.GOING_AWAY, reason="done")
    with pytest.raises(RuntimeError, match="close message"):
        await ws.send_text("x")


@pytest.mark.asyncio
async def test_close_before_accept():
    ws, t = make_ws()
    await ws.close(code=1008)
    assert ws.application_state == WebSocketState.DISCONNECTED
    assert t.sent == [{"type": "websocket.close", "code": 1008, "reason": ""}]


@pytest.mark.asyncio
async def test_http_response_rejection():
    ws, t = make_ws()
    await ws.send({
        "type": "websocket.http.response.start",
        "status": 403,
        "headers": [],
    })
    assert ws.application_state == WebSocketState.RESPONSE
    with pytest.raises(RuntimeError, match="http.response.body"):
        await ws.send({"type": "websocket.send", "text": "x"})
    await ws.send({
        "type": "websocket.http.response.body",
        "body": b"a",
        "more_body": True,
    })
    assert ws.application_state == WebSocketState.RESPONSE
    await ws.send({"type": "websocket.http.response.body", "body": b"b"})
    assert ws.application_state == WebSocketState.DISCONNECTED
    assert len(t.sent) == 3


@pytest.mark.asyncio
async def test_send_os_error_becomes_disconnect():
    ws, t = make_ws([CONNECT])
    await ws.accept()
    t.send_error = OSError("broken pipe")
    with pytest.raises(WebSocketDisconnect) as exc:
        await ws.send_text("x")
    assert exc.value.code == WebSocketClose.ABNORMAL_CLOSURE
    assert ws.application_state == WebSocketState.DISCONNECTED


def test_connection_details_match_django_request():
    ws, _ = make_ws(
        scope={
            "query_string": "q=ñandú&raw=%C3%B1".encode(),
            "headers": [(b"x-token", b"abc"), (b"x_spoofed", b"1")],
        }
    )
    assert ws.query_params["q"] == "ñandú"
    assert ws.query_params["raw"] == "ñ"
    assert ws.headers["X-Token"] == ws.headers["x-token"] == "abc"
    # like Django, underscores are dropped to prevent header spoofing
    assert "x_spoofed" not in ws.headers
    assert ws.query_params is ws.request.GET
