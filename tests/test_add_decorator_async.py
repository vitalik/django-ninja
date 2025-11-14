import asyncio
from functools import wraps

import pytest

from ninja import NinjaAPI, Router
from ninja.testing import TestAsyncClient, TestClient


# Async test decorators
def async_operation_decorator(func):
    """Async decorator that adds data after validation (operation level)"""

    @wraps(func)
    async def wrapper(request, *args, **kwargs):
        result = await func(request, *args, **kwargs)
        if isinstance(result, dict):
            result["async_operation_decorated"] = True
        return result

    return wrapper


def async_view_decorator(func):
    """Async decorator that adds a header before validation (view level)"""

    @wraps(func)
    async def wrapper(request, *args, **kwargs):
        response = await func(request, *args, **kwargs)
        response["X-Async-View-Decorator"] = "applied"
        return response

    return wrapper


@pytest.mark.asyncio
async def test_router_add_decorator_async_operation_mode():
    """Test add_decorator on router with async operations in OPERATION mode"""
    api = NinjaAPI()
    router = Router()

    # Add decorator to router
    router.add_decorator(async_operation_decorator, mode="operation")

    @router.get("/test")
    async def endpoint(request):
        await asyncio.sleep(0)  # Simulate async work
        return {"message": "async test"}

    api.add_router("/", router)
    client = TestAsyncClient(api)

    response = await client.get("/test")
    assert response.status_code == 200
    assert response.json() == {
        "message": "async test",
        "async_operation_decorated": True,
    }


@pytest.mark.asyncio
async def test_router_add_decorator_async_view_mode():
    """Test add_decorator on router with async operations in VIEW mode"""
    api = NinjaAPI()
    router = Router()

    # Add decorator to router
    router.add_decorator(async_view_decorator, mode="view")

    @router.get("/test")
    async def endpoint(request):
        await asyncio.sleep(0)
        return {"message": "async test"}

    api.add_router("/", router)
    client = TestAsyncClient(api)

    response = await client.get("/test")
    assert response.status_code == 200
    assert response["X-Async-View-Decorator"] == "applied"
    assert response.json() == {"message": "async test"}


@pytest.mark.asyncio
async def test_api_add_decorator_async():
    """Test add_decorator on API with async operations"""
    api = NinjaAPI()

    # Add decorator to entire API
    api.add_decorator(async_operation_decorator, mode="operation")

    @api.get("/test1")
    async def endpoint1(request):
        await asyncio.sleep(0)
        return {"message": "test1"}

    @api.get("/test2")
    async def endpoint2(request):
        await asyncio.sleep(0)
        return {"message": "test2"}

    client = TestAsyncClient(api)

    # Both endpoints should be decorated
    response = await client.get("/test1")
    assert response.status_code == 200
    assert response.json() == {"message": "test1", "async_operation_decorated": True}

    response = await client.get("/test2")
    assert response.status_code == 200
    assert response.json() == {"message": "test2", "async_operation_decorated": True}


@pytest.mark.asyncio
async def test_mixed_sync_async_decorators():
    """Test that sync decorators work with async endpoints"""
    api = NinjaAPI()
    router = Router()

    # Use a sync decorator on async endpoint
    def sync_decorator(func):
        @wraps(func)
        def wrapper(request, *args, **kwargs):
            # For async functions, this will return a coroutine
            result = func(request, *args, **kwargs)
            if asyncio.iscoroutine(result):

                async def async_wrapper():
                    actual_result = await result
                    if isinstance(actual_result, dict):
                        actual_result["sync_decorated"] = True
                    return actual_result

                return async_wrapper()
            else:
                # For sync functions, modify the result directly
                if isinstance(result, dict):
                    result["sync_decorated"] = True
                return result

        return wrapper

    router.add_decorator(sync_decorator, mode="operation")

    @router.get("/async")
    async def async_endpoint(request):
        await asyncio.sleep(0)
        return {"type": "async"}

    @router.get("/sync")
    def sync_endpoint(request):
        return {"type": "sync"}

    api.add_router("/", router)
    client = TestAsyncClient(api)

    # Test async endpoint
    response = await client.get("/async")
    assert response.status_code == 200
    assert response.json() == {"type": "async", "sync_decorated": True}

    # Test sync endpoint with regular TestClient
    from ninja.testing import TestClient

    sync_client = TestClient(api)
    response = sync_client.get("/sync")
    assert response.status_code == 200
    assert response.json() == {"type": "sync", "sync_decorated": True}


@pytest.mark.asyncio
async def test_mixed_sync_async_endpoints_same_router():
    """Test router with both sync and async endpoints using the same decorator"""
    api = NinjaAPI()
    router = Router()

    # Universal decorator that works with both sync and async functions
    def universal_decorator(func):
        if asyncio.iscoroutinefunction(func):
            # Handle async functions
            @wraps(func)
            async def async_wrapper(request, *args, **kwargs):
                result = await func(request, *args, **kwargs)
                if isinstance(result, dict):
                    result["universal_decorated"] = True
                    result["func_type"] = "async"
                return result

            return async_wrapper
        else:
            # Handle sync functions
            @wraps(func)
            def sync_wrapper(request, *args, **kwargs):
                result = func(request, *args, **kwargs)
                if isinstance(result, dict):
                    result["universal_decorated"] = True
                    result["func_type"] = "sync"
                return result

            return sync_wrapper

    router.add_decorator(universal_decorator, mode="operation")

    @router.get("/async")
    async def async_endpoint(request):
        await asyncio.sleep(0)
        return {"endpoint": "async"}

    @router.get("/sync")
    def sync_endpoint(request):
        return {"endpoint": "sync"}

    api.add_router("/", router)

    # Test both endpoints with appropriate clients
    async_client = TestAsyncClient(api)
    sync_client = TestClient(api)

    # Test async endpoint
    response = await async_client.get("/async")
    assert response.status_code == 200
    assert response.json() == {
        "endpoint": "async",
        "universal_decorated": True,
        "func_type": "async",
    }

    # Test sync endpoint
    response = sync_client.get("/sync")
    assert response.status_code == 200
    assert response.json() == {
        "endpoint": "sync",
        "universal_decorated": True,
        "func_type": "sync",
    }
