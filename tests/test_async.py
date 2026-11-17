import asyncio
from unittest import mock

import pytest
from asgiref.sync import sync_to_async

from ninja import NinjaAPI
from ninja.security import APIKeyQuery
from ninja.testing import TestAsyncClient
from ninja.throttling import BaseThrottle


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


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "path,thread_hops",
    [
        ("/no-checks", 0),
        ("/sync-auth?key=k", 1),
        ("/throttle", 1),
        # sync auth and throttles run together in one thread hop
        ("/sync-auth-throttle?key=k", 1),
        # async auth runs on the event loop, only throttles need a thread
        ("/async-auth?key=k", 0),
        ("/async-auth-throttle?key=k", 1),
    ],
)
async def test_async_view_checks_thread_hops(path, thread_hops):
    class SyncAuth(APIKeyQuery):
        def authenticate(self, request, key):
            return key

    class AsyncAuth(APIKeyQuery):
        async def authenticate(self, request, key):
            return key

    class Throttle(BaseThrottle):
        def allow_request(self, request):
            return True

    api = NinjaAPI()

    @api.get("/no-checks")
    @api.get("/sync-auth", auth=SyncAuth())
    @api.get("/throttle", throttle=Throttle())
    @api.get("/sync-auth-throttle", auth=SyncAuth(), throttle=Throttle())
    @api.get("/async-auth", auth=AsyncAuth())
    @api.get("/async-auth-throttle", auth=AsyncAuth(), throttle=Throttle())
    async def view(request):
        return {"auth": getattr(request, "auth", None)}

    client = TestAsyncClient(api)

    with mock.patch("ninja.operation.sync_to_async", wraps=sync_to_async) as hop:
        res = await client.get(path)

    assert res.status_code == 200
    assert res.json() == {"auth": "k" if "auth" in path else None}
    assert hop.call_count == thread_hops
