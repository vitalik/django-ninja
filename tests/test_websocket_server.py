"""
End-to-end tests against a real ASGI server (uvicorn) and websocket client.

Skipped when uvicorn/websockets are not installed (they are only part of
the "test" dependency group, never runtime dependencies).
"""

import logging
import socket
import threading
import time

import pytest
from ws_util import api_urlconf, unique_namespace

from ninja import NinjaAPI, WebSocket
from ninja.asgi import NinjaASGI
from ninja.errors import HttpError
from ninja.security import APIKeyQuery

uvicorn = pytest.importorskip("uvicorn")
ws_client = pytest.importorskip("websockets.sync.client")
ws_exceptions = pytest.importorskip("websockets.exceptions")

pytestmark = [
    pytest.mark.django_db(transaction=True),
    # testing the deprecated implementation on purpose
    pytest.mark.filterwarnings("ignore:The `websockets` implementation is deprecated"),
    pytest.mark.filterwarnings("ignore::DeprecationWarning:websockets.legacy"),
]


class KeyQuery(APIKeyQuery):
    def authenticate(self, request, key):
        return key == "secret" and key


def make_api():
    api = NinjaAPI(urls_namespace=unique_namespace())

    @api.websocket("/echo/{room}")
    async def echo(websocket: WebSocket, room: str, times: int = 1):
        await websocket.accept()
        async for message in websocket.iter_json():
            await websocket.send_json({"room": room, "echo": [message] * times})

    @api.websocket("/private", auth=KeyQuery())
    async def private(websocket: WebSocket):
        await websocket.accept()
        await websocket.send_text(f"hello {websocket.auth}")

    @api.websocket("/rooms/{room_id}")
    async def rooms(websocket: WebSocket, room_id: int):
        raise HttpError(404, "Room not found")

    return api


# uvicorn's websocket implementations differ (e.g. "websockets" raises if the
# app sends anything after the client disconnected): test with each of them
WS_IMPLEMENTATIONS = ["websockets", "websockets-sansio"]


@pytest.fixture(params=WS_IMPLEMENTATIONS)
def server(request, settings, caplog):
    settings.ALLOWED_HOSTS = ["127.0.0.1"]
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.bind(("127.0.0.1", 0))
    port = sock.getsockname()[1]

    app = NinjaASGI(urlconf=api_urlconf(make_api()))
    config = uvicorn.Config(app, lifespan="off", log_level="warning", ws=request.param)
    server = uvicorn.Server(config)
    thread = threading.Thread(target=server.run, kwargs={"sockets": [sock]})
    thread.start()
    deadline = time.monotonic() + 10
    while not server.started:
        assert time.monotonic() < deadline, "uvicorn did not start"
        time.sleep(0.01)
    try:
        yield f"ws://127.0.0.1:{port}"
    finally:
        server.should_exit = True
        thread.join(10)
        sock.close()
    # no "Exception in ASGI application" (or any other error) on the server
    errors = [r for r in caplog.records if r.levelno >= logging.ERROR]
    assert errors == [], [r.getMessage() for r in errors]


def rejection(url, **kwargs):
    with pytest.raises(ws_exceptions.InvalidStatus) as exc:
        with ws_client.connect(url, **kwargs):
            pass  # pragma: no cover
    return exc.value.response


def test_echo_with_params(server):
    with ws_client.connect(f"{server}/api/echo/lobby?times=2") as ws:
        ws.send('{"a": 1}')
        assert ws.recv() == '{"room": "lobby", "echo": [{"a": 1}, {"a": 1}]}'


def test_handshake_rejections(server):
    response = rejection(f"{server}/api/private?key=wrong")
    assert response.status_code == 401
    assert response.body == b'{"detail": "Unauthorized"}'

    response = rejection(f"{server}/api/echo/lobby?times=x")
    assert response.status_code == 422

    response = rejection(f"{server}/api/rooms/7")
    assert (response.status_code, response.body) == (
        404,
        b'{"detail": "Room not found"}',
    )

    response = rejection(f"{server}/api/missing")
    assert response.status_code == 404

    response = rejection(
        f"{server}/api/private?key=secret", origin="https://evil.example"
    )
    assert response.status_code == 403


def test_authenticated(server):
    with ws_client.connect(f"{server}/api/private?key=secret") as ws:
        assert ws.recv() == "hello secret"
