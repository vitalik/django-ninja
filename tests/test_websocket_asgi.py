import json
import logging

import pytest
from django.test import override_settings
from django.urls import path, reverse
from django.urls.exceptions import NoReverseMatch
from ws_util import (
    CONNECT,
    FakeTransport,
    api_urlconf,
    connect,
    make_scope,
    unique_namespace,
)

from ninja import NinjaAPI, Router, WebSocket, WebSocketDisconnect
from ninja.asgi import NinjaASGI, _get_script_prefix, get_asgi_application
from ninja.testing import TestClient

# request_started/finished signals run close_old_connections()
pytestmark = pytest.mark.django_db


def make_api():
    api = NinjaAPI(urls_namespace=unique_namespace())
    router = Router()

    @api.websocket("/echo")
    async def echo(websocket: WebSocket):
        await websocket.accept()
        async for message in websocket.iter_text():
            await websocket.send_text(message)

    @router.websocket("/rooms/{int:room_id}", url_name="room")
    async def room(websocket: WebSocket, room_id: int, name: str = "anon"):
        await websocket.accept()
        await websocket.send_json({"room": room_id, "name": name})
        await websocket.close(code=4000)

    @router.websocket("/boom")
    async def boom(websocket: WebSocket):
        await websocket.accept()
        raise ValueError("boom")

    @router.websocket("/gone")
    async def gone(websocket: WebSocket):
        await websocket.accept()
        await websocket.receive_text()

    @router.websocket("/reject")
    async def reject(websocket: WebSocket):
        pass

    @router.get("/shared")
    def shared_http(request):
        return {"http": True}

    @router.websocket("/shared")
    async def shared_ws(websocket: WebSocket):
        await websocket.accept()
        await websocket.send_text("ws")

    api.add_router("/chat", router, url_name_prefix="chat")
    return api


@pytest.mark.asyncio
async def test_echo_and_auto_close():
    app = NinjaASGI(urlconf=api_urlconf(make_api()))
    t = await connect(
        app,
        "/api/echo",
        [
            {"type": "websocket.connect"},
            {"type": "websocket.receive", "text": "hello"},
        ],
    )
    assert t.sent[0]["type"] == "websocket.accept"
    assert t.sent[1] == {"type": "websocket.send", "text": "hello"}
    # the client disconnected (ending iter_text): nothing else may be sent
    assert len(t.sent) == 2


@pytest.mark.asyncio
async def test_handler_returning_while_connected_closes_with_1000():
    api = NinjaAPI(urls_namespace=unique_namespace())

    @api.websocket("/ws")
    async def ws(websocket: WebSocket):
        await websocket.accept()
        await websocket.send_text("bye")

    t = await connect(NinjaASGI(urlconf=api_urlconf(api)), "/api/ws")
    assert t.sent[-1] == {"type": "websocket.close", "code": 1000, "reason": ""}


@pytest.mark.asyncio
async def test_path_params_converters_and_root_path():
    app = NinjaASGI(urlconf=api_urlconf(make_api()))
    t = await connect(
        app, "/prefix/api/chat/rooms/5", query=b"name=bob", root_path="/prefix"
    )
    assert t.sent[1] == {"type": "websocket.send", "text": '{"room": 5, "name": "bob"}'}
    # handler closed by itself: no extra close
    assert t.types == ["websocket.accept", "websocket.send", "websocket.close"]
    assert t.sent[2]["code"] == 4000


@pytest.mark.asyncio
async def test_not_found():
    urlconf = api_urlconf(make_api())
    urlconf.urlpatterns.append(path("plain/", lambda request: None))
    app = NinjaASGI(urlconf=urlconf)
    for p in ("/nope", "/plain/"):
        t = await connect(app, p)
        assert t.sent == [
            {"type": "websocket.close", "code": 1008, "reason": "Not Found"}
        ]


@pytest.mark.asyncio
async def test_handler_error_closes_with_1011(caplog):
    app = NinjaASGI(urlconf=api_urlconf(make_api()))
    with caplog.at_level(logging.ERROR, logger="ninja.websockets"):
        t = await connect(app, "/api/chat/boom")
    assert t.sent[-1] == {"type": "websocket.close", "code": 1011, "reason": ""}
    assert "Error in websocket handler for /api/chat/boom" in caplog.text


@pytest.mark.asyncio
async def test_client_disconnect_is_silent():
    app = NinjaASGI(urlconf=api_urlconf(make_api()))
    t = await connect(app, "/api/chat/gone")
    assert t.types == ["websocket.accept"]


@pytest.mark.asyncio
async def test_handler_returning_without_accept_rejects():
    app = NinjaASGI(urlconf=api_urlconf(make_api()))
    t = await connect(app, "/api/chat/reject")
    assert t.sent == [{"type": "websocket.close", "code": 1000, "reason": ""}]


@pytest.mark.asyncio
async def test_close_on_broken_connection_is_ignored():
    api = NinjaAPI(urls_namespace=unique_namespace())

    @api.websocket("/once")
    async def once(websocket: WebSocket):
        await websocket.accept()

    class BrokenOnClose(FakeTransport):
        async def send(self, message):
            if message["type"] == "websocket.close":
                raise OSError("broken")
            await super().send(message)

    transport = BrokenOnClose()
    app = NinjaASGI(urlconf=api_urlconf(api))
    await app(make_scope("/api/once"), transport.receive, transport.send)
    assert transport.types == ["websocket.accept"]


@pytest.mark.asyncio
async def test_shared_http_and_websocket_path():
    api = make_api()
    app = NinjaASGI(urlconf=api_urlconf(api))
    t = await connect(app, "/api/chat/shared")
    assert t.sent[1] == {"type": "websocket.send", "text": "ws"}

    client = TestClient(api)
    assert client.get("/chat/shared").json() == {"http": True}


@pytest.mark.asyncio
async def test_http_is_forwarded():
    calls = []

    async def inner(scope, receive, send):
        calls.append(scope["type"])

    app = NinjaASGI(inner)
    await app({"type": "http"}, None, None)
    await app({"type": "lifespan"}, None, None)
    assert calls == ["http", "lifespan"]

    with pytest.raises(RuntimeError, match="without an inner application"):
        await NinjaASGI()({"type": "http"}, None, None)


def test_get_asgi_application():
    app = get_asgi_application()
    assert isinstance(app, NinjaASGI)
    assert app.app is not None


def test_script_prefix(settings):
    assert _get_script_prefix({"root_path": "/x"}) == "/x"
    assert _get_script_prefix({}) == ""
    settings.FORCE_SCRIPT_NAME = "/forced"
    assert _get_script_prefix({"root_path": "/x"}) == "/forced"


def test_http_mirror_view():
    client = TestClient(make_api())

    res = client.get("/echo")
    assert res.status_code == 426
    assert res.json() == {"detail": "This endpoint only accepts WebSocket connections."}

    res = client.get("/echo", headers={"Upgrade": "websocket"})
    assert res.status_code == 426
    assert "ASGI server" in res.json()["detail"]
    assert "ninja.asgi.get_asgi_application()" in res.json()["detail"]


def test_reverse_websocket_routes():
    api = make_api()
    urlconf = api_urlconf(api)
    ns = api.urls_namespace
    assert reverse(f"{ns}:echo", urlconf=urlconf) == "/api/echo"
    assert (
        reverse(f"{ns}:room", kwargs={"room_id": 3}, urlconf=urlconf)
        == "/api/chat/rooms/3"
    )
    assert reverse(f"{ns}:chat_boom", urlconf=urlconf) == "/api/chat/boom"
    with pytest.raises(NoReverseMatch):
        reverse(f"{ns}:boom", urlconf=urlconf)


def test_disconnect_exception_is_exported():
    assert issubclass(WebSocketDisconnect, Exception)


@pytest.mark.asyncio
async def test_disallowed_host_is_rejected(caplog):
    app = NinjaASGI(urlconf=api_urlconf(make_api()))
    evil = [(b"host", b"evil.example")]

    with caplog.at_level(logging.ERROR, logger="django.security.DisallowedHost"):
        t = await connect(app, "/api/echo", host=False, headers=evil)
    assert t.sent == [
        {"type": "websocket.close", "code": 1008, "reason": "Invalid Host header"}
    ]
    assert "evil.example" in caplog.text

    t = await connect(
        app,
        "/api/echo",
        host=False,
        headers=evil,
        extensions={"websocket.http.response": {}},
    )
    assert t.sent[0]["status"] == 400


@pytest.mark.asyncio
async def test_got_request_exception_signal():
    import sys

    from django.core.signals import got_request_exception

    received = []

    def receiver(sender, request, **kwargs):
        received.append((sender, request.path, repr(sys.exc_info()[1])))

    got_request_exception.connect(receiver)
    try:
        app = NinjaASGI(urlconf=api_urlconf(make_api()))
        await connect(app, "/api/chat/boom")
    finally:
        got_request_exception.disconnect(receiver)
    assert received == [(None, "/api/chat/boom", "ValueError('boom')")]


@pytest.mark.asyncio
async def test_websocket_exception_closes_with_code():
    from ninja import WebSocketException

    def auth(request):
        if request.GET.get("ban"):
            raise WebSocketException(code=4003, reason="banned")
        return True

    api = NinjaAPI(urls_namespace=unique_namespace())

    @api.websocket("/before", auth=auth)
    async def before(websocket: WebSocket):
        raise WebSocketException(code=4000, reason="x" * 200)

    @api.websocket("/after")
    async def after(websocket: WebSocket):
        await websocket.accept()
        raise WebSocketException(code=4001)

    app = NinjaASGI(urlconf=api_urlconf(api))

    # before accept: the handshake is rejected with the code
    t = await connect(app, "/api/before")
    assert t.types == ["websocket.close"]
    assert t.sent[0]["code"] == 4000
    assert len(t.sent[0]["reason"].encode()) <= 123

    t = await connect(app, "/api/after")
    assert t.sent[1] == {"type": "websocket.close", "code": 4001, "reason": ""}

    # raised from an auth callback
    t = await connect(app, "/api/before", query=b"ban=1")
    assert t.sent == [{"type": "websocket.close", "code": 4003, "reason": "banned"}]


@pytest.mark.asyncio
async def test_urlconf_per_connection():
    api_a = make_api()
    api_b = NinjaAPI(urls_namespace=unique_namespace())

    @api_b.websocket("/echo")
    async def other(websocket: WebSocket):
        await websocket.accept()
        await websocket.send_text("from b")

    class PerHost(NinjaASGI):
        def get_urlconf(self, websocket):
            if websocket.request.get_host() == "b.testserver":
                return api_urlconf(api_b)
            return super().get_urlconf(websocket)

    app = PerHost(urlconf=api_urlconf(api_a))
    with override_settings(ALLOWED_HOSTS=["testserver", "b.testserver"]):
        t = await connect(
            app, "/api/echo", host=False, headers=[(b"host", b"b.testserver")]
        )
        assert t.sent[1] == {"type": "websocket.send", "text": "from b"}
        t = await connect(
            app,
            "/api/echo",
            incoming=[CONNECT, {"type": "websocket.receive", "text": "a"}],
        )
        assert t.sent[1] == {"type": "websocket.send", "text": "a"}


@pytest.mark.asyncio
async def test_routes_match_in_declaration_order():
    api = NinjaAPI(urls_namespace=unique_namespace())
    router = Router()

    @router.websocket("/live")
    async def live(websocket: WebSocket):
        await websocket.accept()
        await websocket.send_text("live")

    @router.get("/{slug}")
    def detail(request, slug: str):
        return {"slug": slug}

    @router.websocket("/{slug}/feed")
    async def feed(websocket: WebSocket, slug: str):
        await websocket.accept()
        await websocket.send_text(slug)

    api.add_router("/ev", router)
    app = NinjaASGI(urlconf=api_urlconf(api))

    # the websocket declared before the HTTP catch-all is not shadowed by it
    t = await connect(app, "/api/ev/live")
    assert t.sent[1] == {"type": "websocket.send", "text": "live"}
    t = await connect(app, "/api/ev/x/feed")
    assert t.sent[1] == {"type": "websocket.send", "text": "x"}
    assert TestClient(api).get("/ev/other").json() == {"slug": "other"}


def test_reverse_websocket_sharing_path_with_http():
    api = NinjaAPI(urls_namespace=unique_namespace())

    # websocket declared first: HTTP requests must still reach the HTTP view
    @api.websocket("/room", url_name="room_ws")
    async def room_ws(websocket: WebSocket):
        pass  # pragma: no cover

    @api.get("/room", url_name="room_http")
    def room_http(request):
        return 1

    assert TestClient(api).get("/room").json() == 1

    urlconf = api_urlconf(api)
    ns = api.urls_namespace
    assert reverse(f"{ns}:room_http", urlconf=urlconf) == "/api/room"
    assert reverse(f"{ns}:room_ws", urlconf=urlconf) == "/api/room"


def test_paths_added_without_router_api_are_kept():
    router = Router()

    @router.get("/a")
    def a(request):
        return "a"

    @router.websocket("/b")
    async def b(websocket: WebSocket):
        pass  # pragma: no cover

    router._route_order.clear()  # as if added directly to the dicts
    api = NinjaAPI(urls_namespace=unique_namespace())
    api.add_router("", router)
    names = [p.name for p in api.urls[0]]
    assert names.index("a") < names.index("b")


@pytest.mark.asyncio
async def test_malformed_client_input_is_not_a_server_error(caplog):
    from django.core.signals import got_request_exception

    from ninja.errors import ValidationError

    api = NinjaAPI(urls_namespace=unique_namespace())

    @api.websocket("/json")
    async def json_handler(websocket: WebSocket):
        await websocket.accept()
        try:
            await websocket.receive_json()
        except ValidationError as e:
            await websocket.send_json(e.errors)
        await websocket.receive_json(mode="binary")  # uncaught this time

    @api.websocket("/text")
    async def text_handler(websocket: WebSocket):
        await websocket.accept()
        await websocket.receive_text()

    signals = []

    def receiver(**kwargs):
        signals.append(kwargs)  # pragma: no cover

    app = NinjaASGI(urlconf=api_urlconf(api))
    got_request_exception.connect(receiver)
    try:
        with caplog.at_level(logging.ERROR):
            t = await connect(
                app,
                "/api/json",
                incoming=[
                    CONNECT,
                    {"type": "websocket.receive", "text": "not json"},
                    {"type": "websocket.receive", "bytes": b"\xff\xfe broken"},
                ],
            )
            t2 = await connect(
                app,
                "/api/text",
                incoming=[CONNECT, {"type": "websocket.receive", "bytes": b"x"}],
            )
    finally:
        got_request_exception.disconnect(receiver)

    errors = json.loads(t.sent[1]["text"])
    assert errors[0]["type"] == "json_invalid"
    assert errors[0]["msg"].startswith("Invalid JSON: ")
    assert t.sent[2]["type"] == "websocket.close"
    assert t.sent[2]["code"] == 1008

    assert t2.sent[-1] == {
        "type": "websocket.close",
        "code": 1003,
        "reason": "Expected a text frame",
    }
    # client mistakes are neither logged as errors nor reported
    assert caplog.records == []
    assert signals == []


@pytest.mark.asyncio
async def test_each_connection_has_its_own_sync_thread():
    import threading

    from asgiref.sync import sync_to_async

    seen = []

    def auth(request):
        seen.append(threading.current_thread())
        return True

    api = NinjaAPI(urls_namespace=unique_namespace())

    @api.websocket("/ws", auth=auth)
    async def ws(websocket: WebSocket):
        await websocket.accept()
        seen.append(await sync_to_async(threading.current_thread)())

    app = NinjaASGI(urlconf=api_urlconf(api))
    await connect(app, "/api/ws")
    await connect(app, "/api/ws")
    outside = await sync_to_async(threading.current_thread)()

    # (Thread objects, not idents: the OS reuses idents of finished threads)
    first, second = seen[:2], seen[2:]
    # auth and the handler's sync code share the connection's thread...
    assert first[0] is first[1] and second[0] is second[1]
    # ...which belongs to that connection only, not to the global executor
    assert first[0] is not second[0]
    assert outside not in seen
    # and it ends with the connection
    assert not first[0].is_alive() and not second[0].is_alive()


@pytest.mark.asyncio
async def test_cancellation_propagates_and_is_not_reported(caplog):
    import asyncio

    api = NinjaAPI(urls_namespace=unique_namespace())
    accepted = asyncio.Event()

    @api.websocket("/ws")
    async def ws(websocket: WebSocket):
        await websocket.accept()
        accepted.set()
        await asyncio.Event().wait()  # until the server shuts down

    transport = FakeTransport()
    app = NinjaASGI(urlconf=api_urlconf(api))
    task = asyncio.ensure_future(
        app(make_scope("/api/ws"), transport.receive, transport.send)
    )
    await accepted.wait()
    with caplog.at_level(logging.ERROR):
        task.cancel()
        with pytest.raises(asyncio.CancelledError):
            await task
    assert caplog.records == []


@pytest.mark.asyncio
async def test_intentional_5xx_is_not_reported(caplog):
    from ninja.errors import HttpError

    api = NinjaAPI(urls_namespace=unique_namespace())

    @api.websocket("/ws")
    async def ws(websocket: WebSocket):
        await websocket.accept()
        raise HttpError(503, "Maintenance")

    with caplog.at_level(logging.ERROR):
        t = await connect(NinjaASGI(urlconf=api_urlconf(api)), "/api/ws")
    assert t.sent[-1] == {
        "type": "websocket.close",
        "code": 1011,
        "reason": "Maintenance",
    }
    assert caplog.records == []
