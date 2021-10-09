from unittest import mock

import pytest
from django.conf import settings
from django.views.decorators.csrf import csrf_exempt

from ninja import NinjaAPI
from ninja.errors import ConfigError
from ninja.security import APIKeyCookie
from ninja.testing import TestClient as BaseTestClient


class TestClient(BaseTestClient):
    def _build_request(self, *args, **kwargs):
        request = super()._build_request(*args, **kwargs)
        request._dont_enforce_csrf_checks = False
        return request


csrf_OFF = NinjaAPI(urls_namespace="csrf_OFF")
csrf_ON = NinjaAPI(urls_namespace="csrf_ON", csrf=True)


@csrf_OFF.post("/post")
def post_off(request):
    return {"success": True}


@csrf_ON.post("/post")
def post_on(request):
    return {"success": True}


@csrf_ON.post("/post/csrf_exempt")
@csrf_exempt
def post_on_with_exempt(request):
    return {"success": True}


TOKEN = "1bcdefghij2bcdefghij3bcdefghij4bcdefghij5bcdefghij6bcdefghijABCD"
COOKIES = {settings.CSRF_COOKIE_NAME: TOKEN}


def test_csrf_off():
    client = TestClient(csrf_OFF)
    assert client.post("/post", COOKIES=COOKIES).status_code == 200


def test_csrf_on():
    client = TestClient(csrf_ON)

    assert client.post("/post", COOKIES=COOKIES).status_code == 403

    # check with token in formdata
    response = client.post("/post", {"csrfmiddlewaretoken": TOKEN}, COOKIES=COOKIES)
    assert response.status_code == 200

    # check with headers
    response = client.post("/post", COOKIES=COOKIES, headers={"X-CSRFTOKEN": TOKEN})
    assert response.status_code == 200

    # exempt check
    assert client.post("/post/csrf_exempt", COOKIES=COOKIES).status_code == 200


def test_raises_on_cookie_auth():
    "It should raise if user picked Cookie based auth and csrf=False"

    class Auth(APIKeyCookie):
        def authenticate(self, request, key):
            return request.COOKIES[key] == "foo"

    api = NinjaAPI(auth=Auth(), csrf=False)

    @api.get("/some")
    def some_method(request):
        pass

    with pytest.raises(ConfigError):
        api._validate()

    try:
        import os

        os.environ["NINJA_SKIP_REGISTRY"] = ""

        # Check for wrong error reported
        match = "Looks like you created multiple NinjaAPIs"
        with pytest.raises(ConfigError, match=match):
            api.urls

        # django debug server can attempt to import the urls twice when errors exist
        # verify we get the correct error reported
        match = "Cookie Authentication must be used with CSRF"
        with pytest.raises(ConfigError, match=match):
            with mock.patch("ninja.main._imported_while_running_in_debug_server", True):
                api.urls

    finally:
        os.environ["NINJA_SKIP_REGISTRY"] = "yes"
