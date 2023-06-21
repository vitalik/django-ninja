import asyncio

import django
import pytest

from ninja import NinjaAPI
from ninja.testing import TestAsyncClient


@pytest.mark.skipif(django.VERSION < (3, 1), reason="requires django 3.1 or higher")
@pytest.mark.asyncio
async def test_async_view_handles_async_auth_func():
    api = NinjaAPI()

    async def auth(request):
        key = request.GET.get("key")
        if key == "secret":
            return key

    @api.get("/async", auth=auth)
    async def view(request):
        await asyncio.sleep(0)
        return {"key": request.auth}

    client = TestAsyncClient(api)

    # Actual tests --------------------------------------------------

    # without auth:
    res = await client.get("/async")
    assert res.status_code == 401

    # async successful
    res = await client.get("/async?key=secret")
    assert res.json() == {"key": "secret"}


@pytest.mark.skipif(django.VERSION < (3, 1), reason="requires django 3.1 or higher")
@pytest.mark.asyncio
async def test_async_view_handles_async_auth_cls():
    api = NinjaAPI()

    class Auth:
        async def __call__(self, request):
            key = request.GET.get("key")
            if key == "secret":
                return key

    @api.get("/async", auth=Auth())
    async def view(request):
        await asyncio.sleep(0)
        return {"key": request.auth}

    client = TestAsyncClient(api)

    # Actual tests --------------------------------------------------

    # without auth:
    res = await client.get("/async")
    assert res.status_code == 401

    # async successful
    res = await client.get("/async?key=secret")
    assert res.json() == {"key": "secret"}


@pytest.mark.skipif(django.VERSION < (3, 1), reason="requires django 3.1 or higher")
@pytest.mark.asyncio
async def test_async_view_handles_multi_auth():
    api = NinjaAPI()

    def auth_1(request):
        return None

    async def auth_2(request):
        return None

    async def auth_3(request):
        key = request.GET.get("key")
        if key == "secret":
            return key

    @api.get("/async", auth=[auth_1, auth_2, auth_3])
    async def view(request):
        await asyncio.sleep(0)
        return {"key": request.auth}

    client = TestAsyncClient(api)

    res = await client.get("/async?key=secret")
    assert res.json() == {"key": "secret"}


@pytest.mark.skipif(django.VERSION < (3, 1), reason="requires django 3.1 or higher")
@pytest.mark.asyncio
async def test_async_view_handles_auth_errors():
    api = NinjaAPI()

    async def auth(request):
        raise Exception("boom")

    @api.get("/async", auth=auth)
    async def view(request):
        await asyncio.sleep(0)
        return {"key": request.auth}

    @api.exception_handler(Exception)
    def on_custom_error(request, exc):
        return api.create_response(request, {"custom": True}, status=401)

    client = TestAsyncClient(api)

    res = await client.get("/async?key=secret")
    assert res.json() == {"custom": True}
