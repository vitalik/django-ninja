import asyncio
from typing import List

import pytest

from ninja import Header, NinjaAPI, Query, Router, Schema, WebSocket
from ninja.errors import ConfigError
from ninja.websockets.handshake import truncate_reason
from ninja.websockets.operation import WebSocketOperation


class FakeTransport:
    def __init__(self, incoming):
        self.incoming = list(incoming)
        self.sent = []

    async def receive(self):
        await asyncio.sleep(0)
        return self.incoming.pop(0)

    async def send(self, message):
        self.sent.append(message)


def make_ws(path="/ws", query=b"", headers=None):
    transport = FakeTransport([{"type": "websocket.connect"}])
    scope = {
        "type": "websocket",
        "path": path,
        "query_string": query,
        "headers": headers or [],
        "scheme": "ws",
    }
    return WebSocket(scope, transport.receive, transport.send), transport


def get_routes(api):
    result = {}
    for bound in api._get_bound_routers():
        for route, op in bound.websocket_routes(bound.prefix):
            result[route] = op
    return result


def test_register_on_api_and_routers():
    api = NinjaAPI()
    router = Router()
    child = Router()

    @api.websocket("/ws")
    async def root(websocket: WebSocket):
        pass  # pragma: no cover

    @router.websocket("/rooms/{room_id}")
    async def room(websocket: WebSocket, room_id: int):
        pass  # pragma: no cover

    @child.websocket("/{uuid:key}")
    async def nested(websocket: WebSocket, key: str):
        pass  # pragma: no cover

    router.add_router("/child", child)
    api.add_router("/chat/", router)

    routes = get_routes(api)
    assert set(routes) == {
        "ws",
        "chat/rooms/<room_id>",
        "chat/child/<uuidstr:key>",
    }
    assert isinstance(routes["ws"], WebSocketOperation)
    assert routes["ws"].api is api
    # template operation is not mutated by binding
    assert root._ninja_operation.api is None
    assert routes["ws"] is not root._ninja_operation


def test_router_reused_in_two_apis():
    router = Router()

    @router.websocket("/ws")
    async def handler(websocket: WebSocket):
        pass  # pragma: no cover

    api1, api2 = NinjaAPI(urls_namespace="a"), NinjaAPI(urls_namespace="b")
    api1.add_router("/one", router)
    api2.add_router("/two", router)
    assert get_routes(api1)["one/ws"].api is api1
    assert get_routes(api2)["two/ws"].api is api2


def test_auth_inheritance():
    def api_auth(request):
        return "api"  # pragma: no cover

    def router_auth(request):
        return "router"  # pragma: no cover

    def own_auth(request):
        return "own"  # pragma: no cover

    api = NinjaAPI(auth=api_auth)
    router = Router(auth=router_auth)

    @api.websocket("/a")
    async def a(websocket: WebSocket):
        pass  # pragma: no cover

    @router.websocket("/b")
    async def b(websocket: WebSocket):
        pass  # pragma: no cover

    @router.websocket("/c", auth=[own_auth])
    async def c(websocket: WebSocket):
        pass  # pragma: no cover

    @router.websocket("/d", auth=None)
    async def d(websocket: WebSocket):
        pass  # pragma: no cover

    api.add_router("/r", router)
    routes = get_routes(api)
    assert routes["a"].auth_callbacks == [api_auth]
    assert routes["r/b"].auth_callbacks == [router_auth]
    assert routes["r/c"].auth_callbacks == [own_auth]
    assert routes["r/d"].auth_callbacks == []


def test_auth_inheritance_from_api_only():
    def api_auth(request):
        return "api"  # pragma: no cover

    api = NinjaAPI(auth=api_auth)
    router = Router()

    @router.websocket("/b")
    async def b(websocket: WebSocket):
        pass  # pragma: no cover

    api.add_router("/r", router)
    assert get_routes(api)["r/b"].auth_callbacks == [api_auth]


def test_config_errors():
    router = Router()

    with pytest.raises(ConfigError, match="async def"):

        @router.websocket("/sync")
        def sync_handler(websocket: WebSocket):
            pass  # pragma: no cover

    with pytest.raises(ConfigError, match="annotated with 'WebSocket'"):

        @router.websocket("/noarg")
        async def no_ws(foo: int):
            pass  # pragma: no cover

    class Payload(Schema):
        x: int

    with pytest.raises(ConfigError, match="'body' params"):

        @router.websocket("/body")
        async def body(websocket: WebSocket, payload: Payload):
            pass  # pragma: no cover

    @router.websocket("/dup")
    async def dup(websocket: WebSocket):
        pass  # pragma: no cover

    with pytest.raises(ConfigError, match="already registered"):
        router.add_websocket_operation("/dup", dup)

    with pytest.raises(ConfigError, match="@api.websocket"):

        @router.get("/http")
        async def http_with_ws(request, websocket: WebSocket):
            pass  # pragma: no cover


def test_frozen_router():
    api = NinjaAPI()
    api.urls  # noqa: B018

    async def handler(websocket: WebSocket):
        pass  # pragma: no cover

    with pytest.raises(ConfigError, match="frozen"):
        api.websocket("/late")(handler)


@pytest.mark.asyncio
async def test_run_resolves_params():
    api = NinjaAPI()
    calls = []

    @api.websocket("/rooms/{room_id}")
    async def room(
        websocket: WebSocket,
        room_id: int,
        request,
        tags: List[str] = Query([]),
        lang: str = "en",
        x_token: str = Header(None),
    ):
        calls.append((room_id, tags, lang, x_token, request.path, request.method))
        await websocket.accept()

    op = get_routes(api)["rooms/<room_id>"]
    ws, transport = make_ws(
        "/rooms/7", query=b"tags=a&tags=b", headers=[(b"x-token", b"t0k")]
    )
    await op.run(ws, {"room_id": "7"})

    assert calls == [(7, ["a", "b"], "en", "t0k", "/rooms/7", "GET")]
    assert ws.path_params == {"room_id": "7"}
    assert transport.sent == [
        {"type": "websocket.accept", "subprotocol": None, "headers": []}
    ]
    assert ws.request.scheme == "http"
    assert ws.request is ws.request


@pytest.mark.asyncio
async def test_run_invalid_params_closes_connection():
    api = NinjaAPI()

    @api.websocket("/rooms/{room_id}")
    async def room(websocket: WebSocket, room_id: int, limit: int):
        raise AssertionError("should not be called")  # pragma: no cover

    op = get_routes(api)["rooms/<room_id>"]
    ws, transport = make_ws("/rooms/x")
    await op.run(ws, {"room_id": "x"})
    assert len(transport.sent) == 1
    message = transport.sent[0]
    assert message["type"] == "websocket.close"
    assert message["code"] == 1008
    assert len(message["reason"].encode()) <= 123


def testtruncate_reason():
    assert truncate_reason("short") == "short"
    long_reason = "ñ" * 100
    truncated = truncate_reason(long_reason)
    assert truncated.endswith("...")
    assert len(truncated.encode()) <= 123


@pytest.mark.asyncio
async def test_run_without_params():
    api = NinjaAPI()

    @api.websocket("/ws")
    async def handler(ws: WebSocket):
        await ws.accept()
        await ws.close()

    ws, transport = make_ws()
    await get_routes(api)["ws"].run(ws, {})
    assert [m["type"] for m in transport.sent] == [
        "websocket.accept",
        "websocket.close",
    ]
