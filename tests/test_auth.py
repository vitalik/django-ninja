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
from ninja.testing import TestClient


def callable_auth(request):
    return request.GET.get("auth")


class KeyQuery(APIKeyQuery):
    def authenticate(self, request, key):
        if key == "keyquerysecret":
            return key


class KeyHeader(APIKeyHeader):
    def authenticate(self, request, key):
        if key == "keyheadersecret":
            return key


class CustomException(Exception):
    pass

class KeyHeaderCustomException(APIKeyHeader):
    def authenticate(self, request, key):
        if key != "keyheadersecret":
            raise CustomException
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


def demo_operation(request):
    return {"auth": request.auth}


api = NinjaAPI(csrf=True)

@api.exception_handler(CustomException)
def on_custom_error(request, exc):
    return api.create_response(request, {"custom": True}, status=401)


for path, auth in [
    ("django_auth", django_auth),
    ("callable", callable_auth),
    ("apikeyquery", KeyQuery()),
    ("apikeyheader", KeyHeader()),
    ("apikeycookie", KeyCookie()),
    ("basic", BasicAuth()),
    ("bearer", BearerAuth()),
    ("multiple", [BasicAuth(), BearerAuth()]),
    ("multiple_or", KeyHeader() | BasicAuth() | BearerAuth()),
    ("multiple_and", KeyHeader() & BasicAuth()),
    ("complex_and_or", (KeyHeader() & BasicAuth()) & (KeyHeader() & BasicAuth())),
    ("customexception", KeyHeaderCustomException()),
]:
    api.get(f"/{path}", auth=auth, operation_id=path)(demo_operation)

client = TestClient(api)


class MockUser(str):
    is_authenticated = True

BODY_UNAUTHORIZED_DEFAULT = dict(detail="Unauthorized")

@pytest.mark.parametrize(
    "path,kwargs,expected_code,expected_body",
    [
        ("/django_auth", {}, 401, BODY_UNAUTHORIZED_DEFAULT),
        ("/django_auth", dict(user=MockUser("admin")), 200, dict(auth="admin")),
        ("/callable", {}, 401, BODY_UNAUTHORIZED_DEFAULT),
        ("/callable?auth=demo", {}, 200, dict(auth="demo")),
        ("/apikeyquery", {}, 401, BODY_UNAUTHORIZED_DEFAULT),
        ("/apikeyquery?key=keyquerysecret", {}, 200, dict(auth="keyquerysecret")),
        ("/apikeyheader", {}, 401, BODY_UNAUTHORIZED_DEFAULT),
        ("/apikeyheader", dict(headers={"key": "keyheadersecret"}), 200, dict(auth="keyheadersecret")),
        ("/apikeycookie", {}, 401, BODY_UNAUTHORIZED_DEFAULT),
        ("/apikeycookie", dict(COOKIES={"key": "keycookiersecret"}), 200, dict(auth="keycookiersecret")),
        ("/basic", {}, 401, BODY_UNAUTHORIZED_DEFAULT),
        ("/basic", dict(headers={"Authorization": "Basic YWRtaW46c2VjcmV0"}), 200, dict(auth="admin")),
        ("/basic", dict(headers={"Authorization": "YWRtaW46c2VjcmV0"}), 200, dict(auth="admin")),
        ("/basic", dict(headers={"Authorization": "Basic invalid"}), 401, BODY_UNAUTHORIZED_DEFAULT),
        ("/basic", dict(headers={"Authorization": "some invalid value"}), 401, BODY_UNAUTHORIZED_DEFAULT),
        ("/bearer", {}, 401, BODY_UNAUTHORIZED_DEFAULT),
        ("/bearer", dict(headers={"Authorization": "Bearer bearertoken"}), 200, dict(auth="bearertoken")),
        ("/multiple", dict(headers={"Authorization": "Bearer bearertoken"}), 200, dict(auth="bearertoken")),
        ("/multiple", dict(headers={"Authorization": "YWRtaW46c2VjcmV0"}), 200, dict(auth="admin")),
        ("/multiple_or", dict(headers={"Authorization": "YWRtaW46c2VjcmV0"}), 200, dict(auth="admin")),
        ("/multiple_or", dict(headers={"Authorization": "Bearer bearertoken"}), 200, dict(auth="bearertoken")),
        ("/multiple_or", dict(headers={"Authorization": "some invalid value"}), 401, BODY_UNAUTHORIZED_DEFAULT),
        ("/multiple_and", dict(headers={"Authorization": "YWRtaW46c2VjcmV0", "key": "keyheadersecret"}), 200, dict(auth="keyheadersecret")),
        ("/multiple_and", dict(headers={"Authorization": "YWRtaW46c2VjcmV0"}), 401, BODY_UNAUTHORIZED_DEFAULT),
        ("/complex_and_or", dict(headers={"Authorization": "YWRtaW46c2VjcmV0", "key": "keyheadersecret"}), 200, dict(auth="keyheadersecret")),
        ("/complex_and_or", dict(headers={"Authorization": "YWRtaW46c2VjcmV0", "key": "invalid"}), 401, BODY_UNAUTHORIZED_DEFAULT),
        ("/bearer", dict(headers={"Authorization": "Invalid bearertoken"}), 401, BODY_UNAUTHORIZED_DEFAULT),
        ("/customexception", {}, 401, dict(custom=True)),
        ("/customexception", dict(headers={"key": "keyheadersecret"}), 200, dict(auth="keyheadersecret")),
    ],
)
def test_auth(path, kwargs, expected_code, expected_body, settings):
    settings.DEBUG = True  # <-- making sure all if debug are covered
    response = client.get(path, **kwargs)
    assert response.status_code == expected_code
    assert response.json() == expected_body


def test_schema():
    schema = api.get_openapi_schema()
    assert schema["components"]["securitySchemes"] == {
        "BasicAuth": {"scheme": "basic", "type": "http"},
        "BearerAuth": {"scheme": "bearer", "type": "http"},
        "KeyCookie": {"in": "cookie", "name": "key", "type": "apiKey"},
        "KeyHeader": {"in": "header", "name": "key", "type": "apiKey"},
        "KeyHeaderCustomException": {"in": "header", "name": "key", "type": "apiKey"},
        "KeyQuery": {"in": "query", "name": "key", "type": "apiKey"},
        "SessionAuth": {"in": "cookie", "name": "sessionid", "type": "apiKey"},
    }
    # TODO: Samename for schema check
    # TODO: check operation security attributes


def test_invalid_setup():
    request = Mock()
    headers = {"Authorization": "Bearer test"}
    request.META = {"HTTP_" + k: v for k, v in headers.items()}
    request.headers = headers

    class MyAuth1(AuthBase):
        def callable(self, *args, **kwargs):
            pass

    class MyAuth2(AuthBase):
        openapi_type = "my"

    with pytest.raises(ConfigError):
        MyAuth1()(request)
    with pytest.raises(TypeError):
        MyAuth2()(request)
    with pytest.raises(TypeError):
        APIKeyCookie()(request)
    with pytest.raises(TypeError):
        APIKeyHeader()(request)
    with pytest.raises(TypeError):
        APIKeyQuery()(request)
    with pytest.raises(TypeError):
        HttpBearer()(request)

    headers = {"Authorization": "Basic YWRtaW46c2VjcmV0"}
    request.META = {"HTTP_" + k: v for k, v in headers.items()}
    request.headers = headers

    with pytest.raises(TypeError):
        HttpBasicAuth()(request)
