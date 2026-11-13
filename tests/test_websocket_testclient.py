import pytest
from ws_util import unique_namespace

from ninja import NinjaAPI, Router, WebSocket, WebSocketDisconnect
from ninja.security import APIKeyCookie, APIKeyHeader
from ninja.testing import TestAsyncClient, TestClient, WebSocketDenied


class HeaderKey(APIKeyHeader):
    param_name = "X-Key"

    def authenticate(self, request, key):
        return key == "k" and key


class CookieKey(APIKeyCookie):
    param_name = "token"

    def authenticate(self, request, key):
        return key


def make_api():
    api = NinjaAPI(urls_namespace=unique_namespace())

    @api.websocket("/echo")
    async def echo(websocket: WebSocket):
        await websocket.accept(subprotocol="chat", headers=[(b"x-extra", b"1")])
        while True:
            message = await websocket.receive()
            if message["type"] == "websocket.disconnect":
                return
            if message.get("text") is not None:
                await websocket.send_text(message["text"])
            else:
                await websocket.send_bytes(message["bytes"])

    @api.websocket("/json")
    async def json_echo(websocket: WebSocket, scale: int = 1):
        await websocket.accept()
        data = await websocket.receive_json()
        await websocket.send_json({"value": data["value"] * scale})
        data = await websocket.receive_json(mode="binary")
        await websocket.send_json(data, mode="binary")

    @api.websocket("/secure", auth=HeaderKey())
    async def secure(websocket: WebSocket):
        await websocket.accept()
        await websocket.send_text(websocket.auth)

    @api.websocket("/cookie", auth=CookieKey())
    async def cookie(websocket: WebSocket):
        await websocket.accept()
        await websocket.send_text(websocket.auth)

    @api.websocket("/refuse")
    async def refuse(websocket: WebSocket):
        await websocket.close(code=4001, reason="nope")

    @api.websocket("/bye")
    async def bye(websocket: WebSocket):
        await websocket.accept()
        await websocket.close(code=4002, reason="bye")

    @api.websocket("/broken")
    async def broken(websocket: WebSocket):
        await websocket.accept()
        await websocket.receive_text()
        raise ValueError("handler bug")

    @api.websocket("/broken-early")
    async def broken_early(websocket: WebSocket):
        raise ValueError("early bug")

    return api


def test_sync_echo():
    client = TestClient(make_api())
    with client.websocket_connect("/echo", subprotocols=["chat"]) as ws:
        assert ws.accepted_subprotocol == "chat"
        assert ws.accepted_headers == [(b"x-extra", b"1")]
        ws.send_text("hello")
        assert ws.receive_text() == "hello"
        ws.send_bytes(b"\x00")
        assert ws.receive_bytes() == b"\x00"
        ws.send({"type": "websocket.receive", "text": "raw"})
        assert ws.receive() == {"type": "websocket.send", "text": "raw"}


def test_sync_json_and_query():
    client = TestClient(make_api())
    with client.websocket_connect("/json?scale=3") as ws:
        ws.send_json({"value": 2})
        assert ws.receive_json() == {"value": 6}
        ws.send_json([1, 2], mode="binary")
        assert ws.receive_json(mode="binary") == [1, 2]


def test_explicit_close_by_client():
    client = TestClient(make_api())
    with client.websocket_connect("/echo") as ws:
        ws.close()


def test_auth_headers_and_cookies():
    client = TestClient(make_api(), headers={"X-Key": "k"})
    with client.websocket_connect("/secure") as ws:
        assert ws.receive_text() == "k"

    with pytest.raises(WebSocketDenied) as exc:
        with client.websocket_connect("/secure", headers={"X-Key": "bad"}):
            pass  # pragma: no cover
    assert exc.value.status_code == 401
    assert exc.value.json() == {"detail": "Unauthorized"}

    client = TestClient(make_api(), COOKIES={"token": "from-client"})
    with client.websocket_connect("/cookie") as ws:
        assert ws.receive_text() == "from-client"
    with client.websocket_connect("/cookie", cookies={"token": "override"}) as ws:
        assert ws.receive_text() == "override"


def test_denied_invalid_params():
    client = TestClient(make_api())
    with pytest.raises(WebSocketDenied) as exc:
        with client.websocket_connect("/json?scale=x"):
            pass  # pragma: no cover
    assert exc.value.status_code == 422
    assert exc.value.headers == [(b"content-type", b"application/json")]


def test_closed_before_accept():
    client = TestClient(make_api())
    with pytest.raises(WebSocketDisconnect) as exc:
        with client.websocket_connect("/refuse"):
            pass  # pragma: no cover
    assert (exc.value.code, exc.value.reason) == (4001, "nope")


def test_closed_by_server():
    client = TestClient(make_api())
    with client.websocket_connect("/bye") as ws:
        with pytest.raises(WebSocketDisconnect) as exc:
            ws.receive_text()
        assert exc.value.code == 4002


def test_not_found():
    client = TestClient(make_api())
    with pytest.raises(WebSocketDisconnect) as exc:
        with client.websocket_connect("/missing"):
            pass  # pragma: no cover
    assert exc.value.code == 1008


def test_handler_exceptions_are_raised():
    client = TestClient(make_api())
    with pytest.raises(ValueError, match="handler bug"):
        with client.websocket_connect("/broken") as ws:
            ws.send_text("boom")
            ws.receive_text()

    with pytest.raises(ValueError, match="early bug"):
        with client.websocket_connect("/broken-early"):
            pass  # pragma: no cover


def test_router_client():
    router = Router()

    @router.websocket("/r")
    async def r(websocket: WebSocket):
        await websocket.accept()
        await websocket.send_text("router")

    client = TestClient(router)
    with client.websocket_connect("/r") as ws:
        assert ws.receive_text() == "router"
        # same app/urlconf object reused for following connections
        app = client._websocket_app
    with client.websocket_connect("/r") as ws:
        assert ws.receive_text() == "router"
    assert client._websocket_app is app


@pytest.mark.asyncio
async def test_async_client():
    client = TestAsyncClient(make_api())
    async with client.websocket_connect("/json?scale=2") as ws:
        await ws.send_json({"value": 5})
        assert await ws.receive_json() == {"value": 10}
        await ws.send_json({"b": 1}, mode="binary")
        assert await ws.receive_json(mode="binary") == {"b": 1}

    async with client.websocket_connect("/echo") as ws:
        await ws.send_bytes(b"x")
        assert await ws.receive_bytes() == b"x"
        await ws.send_text("y")
        assert await ws.receive_text() == "y"


@pytest.mark.asyncio
async def test_async_app_finishing_without_close():
    from ninja.testing.websocket import AsyncWebSocketTestSession, build_websocket_scope

    async def app(scope, receive, send):
        await receive()
        await send({"type": "websocket.accept"})

    async with AsyncWebSocketTestSession(app, build_websocket_scope("/x")) as ws:
        with pytest.raises(RuntimeError, match="finished without closing"):
            await ws.receive()


@pytest.mark.asyncio
async def test_chunked_denial_body():
    from ninja.testing.websocket import AsyncWebSocketTestSession, build_websocket_scope

    async def app(scope, receive, send):
        await receive()
        await send({"type": "websocket.http.response.start", "status": 403})
        await send({
            "type": "websocket.http.response.body",
            "body": b"a",
            "more_body": True,
        })
        await send({"type": "websocket.http.response.body", "body": b"b"})

    with pytest.raises(WebSocketDenied) as exc:
        async with AsyncWebSocketTestSession(app, build_websocket_scope("/x")):
            pass  # pragma: no cover
    assert (exc.value.status_code, exc.value.body, exc.value.headers) == (
        403,
        b"ab",
        [],
    )


def test_token_in_subprotocol_header():
    from ninja.security import APIKeyHeader

    class SubprotocolToken(APIKeyHeader):
        param_name = "Sec-WebSocket-Protocol"

        def authenticate(self, request, key):
            name, _, token = (key or "").partition(",")
            if name.strip() == "access_token" and token.strip() == "s3cret":
                return token.strip()

    api = NinjaAPI(urls_namespace=unique_namespace())

    @api.websocket("/ws", auth=SubprotocolToken())
    async def protected(websocket: WebSocket):
        await websocket.accept(subprotocol="access_token")
        await websocket.send_text(websocket.auth)

    client = TestClient(api)
    with client.websocket_connect("/ws", subprotocols=["access_token", "s3cret"]) as ws:
        assert ws.accepted_subprotocol == "access_token"
        assert ws.receive_text() == "s3cret"

    with pytest.raises(WebSocketDenied):
        with client.websocket_connect("/ws", subprotocols=["access_token", "bad"]):
            pass  # pragma: no cover
