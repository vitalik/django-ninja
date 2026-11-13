import asyncio
import json

import pytest
from asgiref.sync import sync_to_async
from ws_util import HTTP_RESPONSE_EXTENSION, api_urlconf, connect, unique_namespace

from ninja import NinjaAPI, WebSocket
from ninja.asgi import NinjaASGI
from ninja.errors import AuthorizationError
from ninja.security import APIKeyCookie, APIKeyQuery, django_auth
from ninja.websockets.handshake import origin_is_allowed

pytestmark = pytest.mark.django_db(transaction=True)

HTTP_EXT = HTTP_RESPONSE_EXTENSION


async def handshake(app, path, query=b"", **scope_kwargs):
    """Connect and return the messages sent by the application."""
    return (await connect(app, path, query=query, **scope_kwargs)).sent


class KeyQuery(APIKeyQuery):
    def authenticate(self, request, key):
        if key == "secret":
            return "user-from-key"


class AsyncKeyQuery(APIKeyQuery):
    param_name = "akey"

    async def authenticate(self, request, key):
        await asyncio.sleep(0)
        if key == "asecret":
            return "async-user"


def forbid(request):
    if request.GET.get("forbid"):
        raise AuthorizationError()


class CookieKey(APIKeyCookie):
    param_name = "token"

    def authenticate(self, request, key):
        return key == "c00kie" and key


def make_app():
    api = NinjaAPI(urls_namespace=unique_namespace())

    async def whoami(websocket: WebSocket, request):
        await websocket.accept()
        await websocket.send_json({
            "auth": str(websocket.auth),
            "req": str(request.auth),
        })

    api.websocket("/key", auth=KeyQuery())(whoami)
    api.websocket("/multi", auth=[forbid, KeyQuery(), AsyncKeyQuery()])(whoami)
    api.websocket("/cookie", auth=CookieKey())(whoami)
    api.websocket("/cookie-nocsrf", auth=CookieKey(csrf=False))(whoami)

    @api.websocket("/session", auth=django_auth)
    async def session(websocket: WebSocket):
        await websocket.accept()
        username = await sync_to_async(lambda: websocket.request.user.username)()
        await websocket.send_text(username)

    @api.websocket("/params")
    async def params(websocket: WebSocket, n: int):
        pass  # pragma: no cover

    return NinjaASGI(urlconf=api_urlconf(api))


@pytest.mark.asyncio
async def test_query_key_auth():
    app = make_app()
    sent = await handshake(app, "/api/key", b"key=secret")
    assert sent[0]["type"] == "websocket.accept"
    assert json.loads(sent[1]["text"]) == {
        "auth": "user-from-key",
        "req": "user-from-key",
    }

    sent = await handshake(app, "/api/key", b"key=wrong")
    assert sent == [{"type": "websocket.close", "code": 1008, "reason": "Unauthorized"}]


@pytest.mark.asyncio
async def test_denied_with_http_response_extension():
    app = make_app()
    sent = await handshake(app, "/api/key", extensions=HTTP_EXT)
    assert sent[0] == {
        "type": "websocket.http.response.start",
        "status": 401,
        "headers": [(b"content-type", b"application/json")],
    }
    assert sent[1] == {
        "type": "websocket.http.response.body",
        "body": b'{"detail": "Unauthorized"}',
    }
    assert len(sent) == 2

    sent = await handshake(app, "/api/params", b"n=x", extensions=HTTP_EXT)
    assert sent[0]["status"] == 422
    detail = json.loads(sent[1]["body"])["detail"]
    assert detail[0]["loc"] == ["query", "n"]


@pytest.mark.asyncio
async def test_validation_error_close_reason_is_json():
    app = make_app()
    sent = await handshake(app, "/api/params", b"n=x")
    assert sent[0]["code"] == 1008
    assert sent[0]["reason"].startswith('[{"type": "int_parsing"')


@pytest.mark.asyncio
async def test_multiple_and_async_callbacks():
    app = make_app()
    sent = await handshake(app, "/api/multi", b"akey=asecret")
    assert json.loads(sent[1]["text"])["auth"] == "async-user"

    sent = await handshake(app, "/api/multi", b"key=secret")
    assert json.loads(sent[1]["text"])["auth"] == "user-from-key"

    sent = await handshake(
        app, "/api/multi", b"forbid=1&key=secret", extensions=HTTP_EXT
    )
    assert sent[0]["status"] == 403
    assert sent[1]["body"] == b'{"detail": "Forbidden"}'


@pytest.mark.asyncio
async def test_cookie_auth_checks_origin():
    app = make_app()
    cookie = (b"cookie", b"token=c00kie")

    # non-browser client (no Origin)
    sent = await handshake(app, "/api/cookie", headers=[cookie])
    assert sent[0]["type"] == "websocket.accept"

    # same origin
    origin = (b"origin", b"http://testserver")
    sent = await handshake(app, "/api/cookie", headers=[cookie, origin])
    assert sent[0]["type"] == "websocket.accept"

    # cross-site websocket hijacking attempt
    evil = (b"origin", b"https://evil.example")
    sent = await handshake(app, "/api/cookie", headers=[cookie, evil])
    assert sent == [
        {"type": "websocket.close", "code": 1008, "reason": "Origin not allowed"}
    ]

    # csrf=False disables the origin check
    sent = await handshake(app, "/api/cookie-nocsrf", headers=[cookie, evil])
    assert sent[0]["type"] == "websocket.accept"


@pytest.mark.asyncio
async def test_session_auth():
    from django.contrib.auth import get_user_model
    from django.contrib.sessions.backends.db import SessionStore

    def create_session():
        user = get_user_model().objects.create_user("wsuser", password="x")
        store = SessionStore()
        store["_auth_user_id"] = str(user.pk)
        store["_auth_user_backend"] = "django.contrib.auth.backends.ModelBackend"
        store["_auth_user_hash"] = user.get_session_auth_hash()
        store.create()
        return store.session_key

    session_key = await sync_to_async(create_session)()
    app = make_app()

    cookie = (b"cookie", f"sessionid={session_key}".encode())
    sent = await handshake(app, "/api/session", headers=[cookie])
    assert sent[1] == {"type": "websocket.send", "text": "wsuser"}

    sent = await handshake(app, "/api/session")
    assert sent[0]["code"] == 1008


class FakeRequest:
    def __init__(self, origin, host="testserver", disallowed=False):
        self.headers = {} if origin is None else {"origin": origin}
        self._host = host
        self._disallowed = disallowed

    def get_host(self):
        if self._disallowed:
            from django.core.exceptions import DisallowedHost

            raise DisallowedHost(self._host)
        return self._host


def test_origin_is_allowed(settings):
    settings.CSRF_TRUSTED_ORIGINS = [
        "https://trusted.example",
        "legacy.example",
        "https://*.wild.example",
        "*.any-scheme.example",
    ]
    assert origin_is_allowed(FakeRequest(None))
    assert origin_is_allowed(FakeRequest("http://testserver"))
    assert origin_is_allowed(FakeRequest("https://trusted.example"))
    assert origin_is_allowed(FakeRequest("http://legacy.example"))
    assert origin_is_allowed(FakeRequest("https://a.wild.example"))
    assert origin_is_allowed(FakeRequest("http://a.any-scheme.example"))
    assert not origin_is_allowed(FakeRequest("http://a.wild.example"))
    assert not origin_is_allowed(FakeRequest("https://other.example"))
    assert not origin_is_allowed(FakeRequest("null"))
    assert not origin_is_allowed(FakeRequest("http://testserver", disallowed=True))


def test_request_without_sessions_or_auth_apps(monkeypatch):
    from django.apps import apps

    def ws():
        return WebSocket({"type": "websocket", "path": "/", "headers": []}, None, None)

    monkeypatch.setattr(apps, "is_installed", lambda name: False)
    request = ws().request
    assert not hasattr(request, "session")
    assert not hasattr(request, "user")

    monkeypatch.setattr(
        apps, "is_installed", lambda name: name == "django.contrib.sessions"
    )
    request = ws().request
    assert hasattr(request, "session")
    assert not hasattr(request, "user")


@pytest.mark.asyncio
async def test_callback_flagged_async_returning_plain_value():
    def flagged(request):
        return "flagged"

    flagged.is_async = True

    api = NinjaAPI(urls_namespace=unique_namespace())

    @api.websocket("/f", auth=flagged)
    async def handler(websocket: WebSocket):
        await websocket.accept()
        await websocket.send_text(websocket.auth)

    app = NinjaASGI(urlconf=api_urlconf(api))
    sent = await handshake(app, "/api/f")
    assert sent[1]["text"] == "flagged"
