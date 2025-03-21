import pytest
from django.conf import settings

from ninja import NinjaAPI
from ninja.testing import TestAsyncClient as BaseTestAsyncClient


class TestAsyncClient(BaseTestAsyncClient):
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
    csrf_ON = NinjaAPI(urls_namespace="csrf_ON", csrf=True)

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
