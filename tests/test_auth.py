import pytest
from unittest.mock import Mock
from ninja import NinjaAPI
from ninja.security import (
    django_auth,
    APIKeyCookie,
    APIKeyHeader,
    APIKeyQuery,
    HttpBearer,
    HttpBasicAuth,
)
from ninja.security.base import AuthBase
from ninja.errors import ConfigError
from client import NinjaClient


def callble_auth(request):
    return request.GET.get("auth")


class KeyQuery(APIKeyQuery):
    def authenticate(self, request, key):
        if key == "keyquerysecret":
            return key


class KeyHeader(APIKeyHeader):
    def authenticate(self, request, key):
        if key == "keyheadersecret":
            return key


class KeyCookie(APIKeyCookie):
    def authenticate(self, request, key):
        if key == "keycookiersecret":
            return key


class BasicAuth(HttpBasicAuth):
    def authenticate(self, request, username, password):
        if username == "admin" and password == "secret":
            return username


class BearerAuth(HttpBearer):
    def authenticate(self, request, token):
        if token == "bearertoken":
            return token


def demo_operaiton(request):
    return {"auth": request.auth}


api = NinjaAPI()

for path, auth in [
    ("django_auth", django_auth),
    ("callable", callble_auth),
    ("apikeyquery", KeyQuery()),
    ("apikeyheader", KeyHeader()),
    ("apikeycookie", KeyCookie()),
    ("basic", BasicAuth()),
    ("bearer", BearerAuth()),
]:
    api.get(f"/{path}", auth=auth)(demo_operaiton)


client = NinjaClient(api)


class MockUser(str):
    is_authenticated = True


@pytest.mark.parametrize(
    "path,kwargs,expected_code",
    [
        ("/django_auth", {}, 401),
        ("/django_auth", dict(user=MockUser("admin")), 200),
        ("/callable", {}, 401),
        ("/callable?auth=demo", {}, 200),
        ("/apikeyquery", {}, 401),
        ("/apikeyquery?key=keyquerysecret", {}, 200),
        ("/apikeyheader", {}, 401),
        ("/apikeyheader", dict(headers={"key": "keyheadersecret"}), 200),
        ("/apikeycookie", {}, 401),
        ("/apikeycookie", dict(COOKIES={"key": "keycookiersecret"}), 200),
        ("/basic", {}, 401),
        ("/basic", dict(headers={"Authorization": "Basic YWRtaW46c2VjcmV0"}), 200),
        ("/basic", dict(headers={"Authorization": "YWRtaW46c2VjcmV0"}), 200),
        ("/basic", dict(headers={"Authorization": "Basic invalid"}), 401),
        ("/basic", dict(headers={"Authorization": "some invalid value"}), 401),
        ("/bearer", {}, 401),
        ("/bearer", dict(headers={"Authorization": "Bearer bearertoken"}), 200),
        ("/bearer", dict(headers={"Authorization": "Invalid bearertoken"}), 401),
    ],
)
def test_auth(path, kwargs, expected_code):
    response = client.get(path, **kwargs)
    assert response.status_code == expected_code


def test_schema():
    schema = api.get_openapi_schema()
    assert schema["components"]["securitySchemes"] == {
        "BasicAuth": {"scheme": "basic", "type": "http"},
        "BearerAuth": {"scheme": "bearer", "type": "http"},
        "KeyCookie": {"in": "cookie", "name": "key", "type": "apiKey"},
        "KeyHeader": {"in": "header", "name": "key", "type": "apiKey"},
        "KeyQuery": {"in": "query", "name": "key", "type": "apiKey"},
    }
    # TODO: Samename for schema check
    # TOOD: check operation security attributes


def test_invalid_setup():
    request = Mock()
    headers = {"Authorization": "Bearer test"}
    request.META = {"HTTP_" + k: v for k, v in headers.items()}
    request.headers = headers

    class MyAuth1(AuthBase):
        pass

    class MyAuth2(AuthBase):
        openapi_type = "my"

    with pytest.raises(ConfigError):
        MyAuth1()(request)
    with pytest.raises(NotImplementedError):
        MyAuth2()(request)
    with pytest.raises(NotImplementedError):
        APIKeyCookie()(request)
    with pytest.raises(NotImplementedError):
        APIKeyHeader()(request)
    with pytest.raises(NotImplementedError):
        APIKeyQuery()(request)
    with pytest.raises(NotImplementedError):
        HttpBearer()(request)

    headers = {"Authorization": "Basic YWRtaW46c2VjcmV0"}
    request.META = {"HTTP_" + k: v for k, v in headers.items()}
    request.headers = headers

    with pytest.raises(NotImplementedError):
        HttpBasicAuth()(request)
