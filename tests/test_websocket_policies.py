"""Handshake policies: origin, throttling, decorators and API exception handlers."""

import pytest
from django.http import HttpRequest
from ws_util import api_urlconf, connect, unique_namespace

from ninja import NinjaAPI, Router, WebSocket
from ninja.asgi import NinjaASGI
from ninja.errors import HttpError
from ninja.testing import TestClient, WebSocketDenied
from ninja.throttling import BaseThrottle

pytestmark = pytest.mark.django_db

EVIL_ORIGIN = [(b"origin", b"https://evil.example")]


class QueryThrottle(BaseThrottle):
    """Denies the handshake when ?block=<name>."""

    def __init__(self, name, wait=2.5):
        self.name = name
        self._wait = wait

    def allow_request(self, request: HttpRequest) -> bool:
        return request.GET.get("block") != self.name

    def wait(self):
        return self._wait


async def echo(websocket: WebSocket):
    await websocket.accept()
    await websocket.send_text("ok")


def bound_operations(api):
    result = {}
    for bound in api._get_bound_routers():
        for route, op in bound.websocket_routes(bound.prefix):
            result[route] = op
    return result


# -- Origin ------------------------------------------------------------------


@pytest.mark.asyncio
async def test_origin_checked_without_auth(settings):
    api = NinjaAPI(urls_namespace=unique_namespace())
    api.websocket("/default")(echo)
    api.websocket("/public", check_origin=False)(echo)
    api.websocket("/strict", check_origin=True)(echo)
    app = NinjaASGI(urlconf=api_urlconf(api))

    t = await connect(app, "/api/default", headers=EVIL_ORIGIN)
    assert t.sent == [
        {"type": "websocket.close", "code": 1008, "reason": "Origin not allowed"}
    ]
    t = await connect(app, "/api/public", headers=EVIL_ORIGIN)
    assert t.types[0] == "websocket.accept"

    # global opt-out, routes can still opt in
    settings.NINJA_WEBSOCKET_CHECK_ORIGIN = False
    t = await connect(app, "/api/default", headers=EVIL_ORIGIN)
    assert t.types[0] == "websocket.accept"
    t = await connect(app, "/api/strict", headers=EVIL_ORIGIN)
    assert t.sent[0]["reason"] == "Origin not allowed"


# -- Throttling --------------------------------------------------------------


def test_throttle_rejects_handshake_with_429():
    api = NinjaAPI(urls_namespace=unique_namespace())
    api.websocket("/ws", throttle=QueryThrottle("op"))(echo)
    client = TestClient(api)

    with client.websocket_connect("/ws") as ws:
        assert ws.receive_text() == "ok"

    with pytest.raises(WebSocketDenied) as exc:
        with client.websocket_connect("/ws?block=op"):
            pass  # pragma: no cover
    assert exc.value.status_code == 429
    assert (b"retry-after", b"3") in exc.value.headers


@pytest.mark.asyncio
async def test_throttle_without_http_response_extension_closes_with_1013():
    api = NinjaAPI(urls_namespace=unique_namespace())
    api.websocket("/ws", throttle=[QueryThrottle("op", wait=None)])(echo)
    t = await connect(NinjaASGI(urlconf=api_urlconf(api)), "/api/ws", query=b"block=op")
    assert t.sent == [
        {"type": "websocket.close", "code": 1013, "reason": "Too many requests."}
    ]


def test_throttle_inheritance():
    api_throttle = QueryThrottle("api")
    router_throttle = QueryThrottle("router")
    own_throttle = QueryThrottle("own")

    api = NinjaAPI(urls_namespace=unique_namespace(), throttle=api_throttle)
    router = Router(throttle=router_throttle)
    api.websocket("/a")(echo)
    router.websocket("/b")(echo)
    router.websocket("/c", throttle=[own_throttle])(echo)
    router.websocket("/d", throttle=[])(echo)
    api.add_router("/r", router)

    ops = bound_operations(api)
    assert ops["a"].throttle_objects == [api_throttle]
    assert ops["r/b"].throttle_objects == [router_throttle]
    assert ops["r/c"].throttle_objects == [own_throttle]
    assert ops["r/d"].throttle_objects == []


def test_no_throttle_anywhere():
    api = NinjaAPI(urls_namespace=unique_namespace())
    api.websocket("/a")(echo)
    assert bound_operations(api)["a"].throttle_objects == []


def test_throttle_list_on_router():
    t1, t2 = QueryThrottle("1"), QueryThrottle("2")
    api = NinjaAPI(urls_namespace=unique_namespace())
    router = Router(throttle=[t1, t2])
    router.websocket("/b")(echo)
    api.add_router("/r", router)
    assert bound_operations(api)["r/b"].throttle_objects == [t1, t2]


def test_invalid_throttle():
    api = NinjaAPI(urls_namespace=unique_namespace())
    with pytest.raises(AssertionError, match="BaseThrottle"):
        api.websocket("/ws", throttle=["nope"])(echo)


# -- Decorators --------------------------------------------------------------


def test_decorators_are_not_applied_and_warn():
    def deco(func):
        return func  # pragma: no cover

    api = NinjaAPI(urls_namespace=unique_namespace())
    api.add_decorator(deco)
    api.websocket("/ws")(echo)

    with pytest.warns(UserWarning, match=r"not applied to websocket handlers \(echo\)"):
        api.urls  # noqa: B018


# -- API exception handlers --------------------------------------------------


class RoomClosed(Exception):
    pass


def make_api():
    api = NinjaAPI(urls_namespace=unique_namespace())

    @api.exception_handler(RoomClosed)
    def room_closed(request, exc):
        response = api.create_response(request, {"detail": "Room closed"}, status=410)
        response.set_cookie("last_room", "1")
        return response

    @api.websocket("/before")
    async def before(websocket: WebSocket):
        raise RoomClosed()

    @api.websocket("/after")
    async def after(websocket: WebSocket):
        await websocket.accept()
        raise HttpError(404, "Room not found")

    @api.websocket("/http-error")
    async def http_error(websocket: WebSocket):
        raise HttpError(404, "Room not found")

    @api.websocket("/after-close")
    async def after_close(websocket: WebSocket):
        await websocket.accept()
        await websocket.close()
        raise RoomClosed()

    @api.websocket("/bug")
    async def bug(websocket: WebSocket):
        await websocket.accept()
        raise ValueError("bug")

    @api.websocket("/bug-before")
    async def bug_before(websocket: WebSocket):
        raise ValueError("bug")

    def failing_auth(request):
        raise RuntimeError("auth backend down")

    @api.websocket("/auth-down", auth=failing_auth)
    async def auth_down(websocket: WebSocket):
        pass  # pragma: no cover

    @api.exception_handler(KeyError)
    def broken_handler(request, exc):
        raise TypeError("handler bug")

    @api.websocket("/broken-handler")
    async def broken(websocket: WebSocket):
        raise KeyError("x")

    return api


def test_custom_exception_handler_before_accept():
    client = TestClient(make_api())
    with pytest.raises(WebSocketDenied) as exc:
        with client.websocket_connect("/before"):
            pass  # pragma: no cover
    assert exc.value.status_code == 410
    assert exc.value.json() == {"detail": "Room closed"}
    cookies = [v for k, v in exc.value.headers if k == b"set-cookie"]
    assert cookies[0].startswith(b"last_room=1")

    with pytest.raises(WebSocketDenied) as exc:
        with client.websocket_connect("/http-error"):
            pass  # pragma: no cover
    assert exc.value.status_code == 404


@pytest.mark.asyncio
async def test_exception_handlers_after_accept_and_without_extension():
    app = NinjaASGI(urlconf=api_urlconf(make_api()))

    t = await connect(app, "/api/after")
    assert t.sent[-1] == {
        "type": "websocket.close",
        "code": 1008,
        "reason": "Room not found",
    }

    t = await connect(app, "/api/before")
    assert t.sent == [
        {"type": "websocket.close", "code": 1008, "reason": "Room closed"}
    ]

    # already closed by the handler: nothing else is sent
    t = await connect(app, "/api/after-close")
    assert t.types == ["websocket.accept", "websocket.close"]


@pytest.mark.asyncio
async def test_unhandled_exception_in_auth_closes_with_1011():
    app = NinjaASGI(urlconf=api_urlconf(make_api()))
    t = await connect(app, "/api/auth-down")
    assert t.sent == [{"type": "websocket.close", "code": 1011, "reason": ""}]


@pytest.mark.asyncio
async def test_exception_handler_failing_propagates():
    app = NinjaASGI(urlconf=api_urlconf(make_api()))
    with pytest.raises(TypeError, match="handler bug"):
        await connect(app, "/api/broken-handler")


@pytest.mark.asyncio
async def test_debug_traceback_response(settings):
    settings.DEBUG = True
    app = NinjaASGI(urlconf=api_urlconf(make_api()))

    # after accept: 5xx -> close 1011 with the status phrase
    t = await connect(app, "/api/bug")
    assert t.sent[-1] == {
        "type": "websocket.close",
        "code": 1011,
        "reason": "Internal Server Error",
    }

    # before accept, with the extension: the traceback response itself
    t = await connect(
        app, "/api/bug-before", extensions={"websocket.http.response": {}}
    )
    assert t.sent[0]["status"] == 500
    assert b"ValueError: bug" in t.sent[1]["body"]
