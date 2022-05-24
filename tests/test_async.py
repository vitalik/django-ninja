import asyncio

import django
import pytest

from ninja import NinjaAPI
from ninja.security import APIKeyQuery
from ninja.testing import TestAsyncClient


@pytest.mark.skipif(django.VERSION < (3, 1), reason="requires django 3.1 or higher")
@pytest.mark.asyncio
async def test_asyncio_operations():
    api = NinjaAPI()

    class KeyQuery(APIKeyQuery):
        def authenticate(self, request, key):
            if key == "secret":
                return key

    @api.get("/async", auth=KeyQuery())
    async def async_view(request, payload: int):
        await asyncio.sleep(0)
        return {"async": True}

    @api.post("/async")
    def sync_post_to_async_view(request):
        return {"sync": True}

    client = TestAsyncClient(api)

    # Actual tests --------------------------------------------------

    # without auth:
    res = await client.get("/async?payload=1")
    assert res.status_code == 401

    # async successful
    res = await client.get("/async?payload=1&key=secret")
    assert res.json() == {"async": True}

    # async innvalid input
    res = await client.get("/async?payload=str&key=secret")
    assert res.status_code == 422

    # async call to sync method for path that have async operations
    res = await client.post("/async")
    assert res.json() == {"sync": True}

    # invalid method
    res = await client.put("/async")
    assert res.status_code == 405
