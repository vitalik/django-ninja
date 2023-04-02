from unittest import mock

import django
import pytest
from django.conf import settings

from ninja import NinjaAPI
from ninja.errors import ConfigError
from ninja.security import APIKeyCookie
from ninja.testing import TestAsyncClient as BaseTestAsyncClient


class TestAsyncClient(BaseTestAsyncClient):
    def _build_request(self, *args, **kwargs):
        request = super()._build_request(*args, **kwargs)
        request._dont_enforce_csrf_checks = False
        return request


csrf_OFF = NinjaAPI(urls_namespace="csrf_OFF")
csrf_ON = NinjaAPI(urls_namespace="csrf_ON", csrf=True)


@csrf_OFF.post("/post")
async def post_off(request):
    return {"success": True}


@csrf_ON.post("/post")
async def post_on(request):
    return {"success": True}


TOKEN = "1bcdefghij2bcdefghij3bcdefghij4bcdefghij5bcdefghij6bcdefghijABCD"
COOKIES = {settings.CSRF_COOKIE_NAME: TOKEN}


@pytest.mark.skipif(django.VERSION < (3, 1), reason="requires django 3.1 or higher")
@pytest.mark.asyncio
async def test_csrf_off():
    client = TestAsyncClient(csrf_OFF)
    response = await client.post("/post", COOKIES=COOKIES)
    assert response.status_code == 200


@pytest.mark.skipif(django.VERSION < (3, 1), reason="requires django 3.1 or higher")
@pytest.mark.asyncio
async def test_csrf_on():
    client = TestAsyncClient(csrf_ON)

    response = await client.post("/post", COOKIES=COOKIES)
    assert response.status_code == 403

    # check with token in formdata
    response = await client.post(
        "/post", {"csrfmiddlewaretoken": TOKEN}, COOKIES=COOKIES
    )
    assert response.status_code == 200

    # check with headers
    response = await client.post(
        "/post", COOKIES=COOKIES, headers={"X-CSRFTOKEN": TOKEN}
    )
    assert response.status_code == 200


@pytest.mark.skipif(django.VERSION < (3, 1), reason="requires django 3.1 or higher")
@pytest.mark.asyncio
async def test_raises_on_cookie_auth():
    "It should raise if user picked Cookie based auth and csrf=False"

    class Auth(APIKeyCookie):
        def authenticate(self, request, key):
            return request.COOKIES[key] == "foo"

    api = NinjaAPI(auth=Auth(), csrf=False)

    @api.get("/some")
    async def some_method(request):
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
