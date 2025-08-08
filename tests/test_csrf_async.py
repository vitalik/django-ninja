import pytest
from django.conf import settings

from ninja import NinjaAPI
from ninja.security import APIKeyCookie
from ninja.testing import TestAsyncClient as BaseTestAsyncClient


class AnyCookieAuth(APIKeyCookie):
    """A mock authentication class that accepts any cookie value.
    To test CSRF functionality without specific authentication logic.
    """

    def authenticate(self, request, key):
        return True


class TestAsyncClient(BaseTestAsyncClient):
    """Custom TestClient that forces CSRF checks"""

    def _build_request(self, *args, **kwargs):
        request = super()._build_request(*args, **kwargs)
        request._dont_enforce_csrf_checks = False
        return request


TOKEN = "1bcdefghij2bcdefghij3bcdefghij4bcdefghij5bcdefghij6bcdefghijABCD"
COOKIES = {settings.CSRF_COOKIE_NAME: TOKEN}


@pytest.mark.asyncio
async def test_csrf_off():
    csrf_OFF = NinjaAPI(urls_namespace="csrf_OFF")

    @csrf_OFF.post("/post")
    async def post_off(request):
        return {"success": True}

    client = TestAsyncClient(csrf_OFF)
    response = await client.post("/post", COOKIES=COOKIES)
    assert response.status_code == 200


@pytest.mark.asyncio
async def test_csrf_on():
    csrf_ON = NinjaAPI(urls_namespace="csrf_ON", auth=AnyCookieAuth())

    @csrf_ON.post("/post")
    async def post_on(request):
        return {"success": True}

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


@pytest.mark.asyncio
async def test_csrf_exempt_async():
    """Test that csrf_exempt functionality works with async operations"""
    csrf_ON = NinjaAPI(urls_namespace="csrf_exempt_async", auth=AnyCookieAuth())

    # Define the async function and manually set csrf_exempt attribute
    async def post_on_with_exempt(request):
        return {"success": True}

    # Manually set the csrf_exempt attribute (simulating what @csrf_exempt would do)
    post_on_with_exempt.csrf_exempt = True

    # Register with the API
    csrf_ON.post("/post/csrf_exempt")(post_on_with_exempt)

    client = TestAsyncClient(csrf_ON)

    # This should succeed even without CSRF token because of csrf_exempt attribute
    response = await client.post("/post/csrf_exempt", COOKIES=COOKIES)
    assert response.status_code == 200
