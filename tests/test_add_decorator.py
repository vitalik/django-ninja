from functools import wraps

import pytest

from ninja import NinjaAPI, Router
from ninja.testing import TestClient


# Test decorators
def operation_decorator(func):
    """Decorator that adds a header after validation (operation level)"""

    @wraps(func)
    def wrapper(request, *args, **kwargs):
        result = func(request, *args, **kwargs)
        if isinstance(result, dict):
            result["operation_decorated"] = True
        return result

    return wrapper


def view_decorator(func):
    """Decorator that adds a header before validation (view level)"""

    @wraps(func)
    def wrapper(request, *args, **kwargs):
        response = func(request, *args, **kwargs)
        response["X-View-Decorator"] = "applied"
        return response

    return wrapper


def counter_decorator(func):
    """Decorator that counts calls"""

    @wraps(func)
    def wrapper(request, *args, **kwargs):
        wrapper.call_count = getattr(wrapper, "call_count", 0) + 1
        result = func(request, *args, **kwargs)
        if isinstance(result, dict):
            result["call_count"] = wrapper.call_count
        return result

    return wrapper


def test_router_add_decorator_operation_mode():
    """Test add_decorator on router with OPERATION mode"""
    api = NinjaAPI()
    router = Router()

    # Add decorator to router
    router.add_decorator(operation_decorator, mode="operation")

    @router.get("/test")
    def endpoint(request):
        return {"message": "test"}

    api.add_router("/", router)
    client = TestClient(api)

    response = client.get("/test")
    assert response.status_code == 200
    assert response.json() == {"message": "test", "operation_decorated": True}


def test_router_add_decorator_view_mode():
    """Test add_decorator on router with VIEW mode"""
    api = NinjaAPI()
    router = Router()

    # Add decorator to router
    router.add_decorator(view_decorator, mode="view")

    @router.get("/test")
    def endpoint(request):
        return {"message": "test"}

    api.add_router("/", router)
    client = TestClient(api)

    response = client.get("/test")
    assert response.status_code == 200
    assert response["X-View-Decorator"] == "applied"
    assert response.json() == {"message": "test"}


def test_api_add_decorator_operation_mode():
    """Test add_decorator on API with OPERATION mode"""
    api = NinjaAPI()

    # Add decorator to entire API
    api.add_decorator(operation_decorator, mode="operation")

    @api.get("/test1")
    def endpoint1(request):
        return {"message": "test1"}

    @api.get("/test2")
    def endpoint2(request):
        return {"message": "test2"}

    client = TestClient(api)

    # Both endpoints should be decorated
    response = client.get("/test1")
    assert response.status_code == 200
    assert response.json() == {"message": "test1", "operation_decorated": True}

    response = client.get("/test2")
    assert response.status_code == 200
    assert response.json() == {"message": "test2", "operation_decorated": True}


def test_api_add_decorator_view_mode():
    """Test add_decorator on API with VIEW mode"""
    api = NinjaAPI()

    # Add decorator to entire API
    api.add_decorator(view_decorator, mode="view")

    @api.get("/test")
    def endpoint(request):
        return {"message": "test"}

    client = TestClient(api)

    response = client.get("/test")
    assert response.status_code == 200
    assert response["X-View-Decorator"] == "applied"


def test_multiple_decorators():
    """Test multiple decorators on same router"""
    api = NinjaAPI()
    router = Router()

    # Add multiple decorators
    router.add_decorator(operation_decorator, mode="operation")
    router.add_decorator(counter_decorator, mode="operation")

    @router.get("/test")
    def endpoint(request):
        return {"message": "test"}

    api.add_router("/", router)
    client = TestClient(api)

    response = client.get("/test")
    assert response.status_code == 200
    result = response.json()
    assert result["message"] == "test"
    assert result["operation_decorated"] is True
    assert result["call_count"] == 1

    # Second call should increment counter
    response = client.get("/test")
    result = response.json()
    assert result["call_count"] == 2


def test_decorator_cascading():
    """Test that decorators cascade from API to router to child router"""
    api = NinjaAPI()
    parent_router = Router()
    child_router = Router()

    # Add decorator at API level
    api.add_decorator(
        lambda f: wraps(f)(lambda req, *a, **k: {**f(req, *a, **k), "api": True})
    )

    # Add decorator at parent router level
    parent_router.add_decorator(
        lambda f: wraps(f)(lambda req, *a, **k: {**f(req, *a, **k), "parent": True})
    )

    # Add decorator at child router level
    child_router.add_decorator(
        lambda f: wraps(f)(lambda req, *a, **k: {**f(req, *a, **k), "child": True})
    )

    @child_router.get("/test")
    def endpoint(request):
        return {"message": "test"}

    parent_router.add_router("/child", child_router)
    api.add_router("/parent", parent_router)

    client = TestClient(api)
    response = client.get("/parent/child/test")
    assert response.status_code == 200
    result = response.json()
    assert result == {
        "message": "test",
        "api": True,
        "parent": True,
        "child": True,
    }


def test_api_decorator_applies_to_new_routers():
    """Test that API-level decorators apply to routers added after decorator"""
    api = NinjaAPI()

    # Add decorator to API first
    api.add_decorator(operation_decorator, mode="operation")

    # Then add a router
    router = Router()

    @router.get("/test")
    def endpoint(request):
        return {"message": "test"}

    api.add_router("/", router)

    client = TestClient(api)
    response = client.get("/test")
    assert response.status_code == 200
    assert response.json() == {"message": "test", "operation_decorated": True}


def test_mix_view_and_operation_decorators():
    """Test mixing VIEW and OPERATION mode decorators"""
    api = NinjaAPI()
    router = Router()

    # Add both types of decorators
    router.add_decorator(view_decorator, mode="view")
    router.add_decorator(operation_decorator, mode="operation")

    @router.get("/test")
    def endpoint(request):
        return {"message": "test"}

    api.add_router("/", router)
    client = TestClient(api)

    response = client.get("/test")
    assert response.status_code == 200
    assert response["X-View-Decorator"] == "applied"
    assert response.json() == {"message": "test", "operation_decorated": True}


def test_decorator_with_path_params():
    """Test decorators work with path parameters"""
    api = NinjaAPI()
    router = Router()

    def param_decorator(func):
        @wraps(func)
        def wrapper(request, *args, **kwargs):
            result = func(request, *args, **kwargs)
            if isinstance(result, dict):
                result["decorated"] = True
            return result

        return wrapper

    router.add_decorator(param_decorator, mode="operation")

    @router.get("/test/{item_id}")
    def endpoint(request, item_id: int):
        return {"item_id": item_id}

    api.add_router("/", router)
    client = TestClient(api)

    response = client.get("/test/123")
    assert response.status_code == 200
    assert response.json() == {"item_id": 123, "decorated": True}


def test_invalid_decorator_mode():
    """Test that invalid decorator mode raises ValueError"""
    router = Router()

    with pytest.raises(ValueError, match="Invalid decorator mode"):
        router.add_decorator(operation_decorator, mode="invalid")  # type: ignore
