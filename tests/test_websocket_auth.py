import asyncio
import json

import pytest
from asgiref.sync import sync_to_async
from django.http import HttpResponse
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

    async def whoami(websocket: WebSocket):
        await websocket.accept()
        await websocket.send_json({
            "auth": str(websocket.auth),
            "req": str(websocket.request.auth),
        })

    api.websocket("/key", auth=KeyQuery())(whoami)
    api.websocket("/multi", auth=[forbid, KeyQuery(), AsyncKeyQuery()])(whoami)
    api.websocket("/cookie", auth=CookieKey())(whoami)
    api.websocket("/cookie-nocsrf", auth=CookieKey(csrf=False))(whoami)
    api.websocket("/cookie-public", auth=CookieKey(csrf=False), check_origin=False)(
        whoami
    )
    api.websocket("/cookie-csrf-wins", auth=CookieKey(), check_origin=False)(whoami)

    @api.websocket("/session", auth=django_auth)
    async def session(websocket: WebSocket):
        await websocket.accept()
        username = await sync_to_async(lambda: websocket.request.user.username)()
        user = await websocket.request.auser()
        assert user is await websocket.request.auser()  # cached
        await websocket.send_text(f"{username}/{user.username}")

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
        "headers": [(b"content-type", b"application/json; charset=utf-8")],
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
async def test_validation_error_close_reason_is_status_phrase():
    app = make_app()
    sent = await handshake(app, "/api/params", b"n=x")
    # the phrase depends on the Python version ("Unprocessable Entity"/"Content")
    phrase = HttpResponse(status=422).reason_phrase
    assert sent == [{"type": "websocket.close", "code": 1008, "reason": phrase}]


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

    # the origin is checked for every handshake by default
    sent = await handshake(app, "/api/cookie-nocsrf", headers=[cookie, evil])
    assert sent[0]["reason"] == "Origin not allowed"

    # it can be disabled per route...
    sent = await handshake(app, "/api/cookie-public", headers=[cookie, evil])
    assert sent[0]["type"] == "websocket.accept"

    # ...unless the cookie auth itself asks for CSRF protection
    sent = await handshake(app, "/api/cookie-csrf-wins", headers=[cookie, evil])
    assert sent[0]["reason"] == "Origin not allowed"


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
    assert sent[1] == {"type": "websocket.send", "text": "wsuser/wsuser"}

    sent = await handshake(app, "/api/session")
    assert sent[0]["code"] == 1008


class FakeRequest:
    def __init__(self, origin, host="testserver", disallowed=False, secure=False):
        self.headers = {} if origin is None else {"origin": origin}
        self._host = host
        self._disallowed = disallowed
        self._secure = secure

    def is_secure(self):
        return self._secure

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
        ".old-style.example",
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

    # the scheme must match the request's (like Django's CSRF Origin check)
    assert not origin_is_allowed(FakeRequest("https://testserver"))
    assert origin_is_allowed(FakeRequest("https://testserver", secure=True))
    assert not origin_is_allowed(FakeRequest("http://testserver", secure=True))
    # case-insensitive, ports are part of the host
    assert origin_is_allowed(FakeRequest("HTTP://TestServer"))
    assert not origin_is_allowed(FakeRequest("http://testserver:8000"))
    assert origin_is_allowed(
        FakeRequest("http://testserver:8000", host="testserver:8000")
    )
    # Django < 4.0 style entries: ".domain" also matches subdomains
    assert origin_is_allowed(FakeRequest("https://old-style.example"))
    assert origin_is_allowed(FakeRequest("https://a.old-style.example"))
    assert not origin_is_allowed(FakeRequest("https://old-style.example.evil"))


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
