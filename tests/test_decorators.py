from functools import wraps
from typing import List

import pytest

from ninja import NinjaAPI
from ninja.decorators import decorate_view
from ninja.pagination import paginate
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
        response["X-View-Decorator"] = "view_decorator"
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


def test_decorator_before():
    api = NinjaAPI()

    @decorate_view(view_decorator)
    @api.get("/before")
    def dec_before(request):
        return 1

    client = TestClient(api)
    response = client.get("/before")
    assert response.status_code == 200
    assert response["X-View-Decorator"] == "view_decorator"


def test_decorator_after():
    api = NinjaAPI()

    @api.get("/after")
    @decorate_view(view_decorator)
    def dec_after(request):
        return 1

    client = TestClient(api)
    response = client.get("/after")
    assert response.status_code == 200
    assert response["X-View-Decorator"] == "view_decorator"


def test_decorator_multiple():
    api = NinjaAPI()

    @api.get("/multi", response=List[int])
    @decorate_view(view_decorator)
    @paginate
    def dec_multi(request):
        return [1, 2, 3, 4]

    client = TestClient(api)
    response = client.get("/multi")
    assert response.status_code == 200
    assert response.json() == {"count": 4, "items": [1, 2, 3, 4]}
    assert response["X-View-Decorator"] == "view_decorator"


def test_decorator_operation_mode_on_top_of_api_method():
    """
    Test decorate_view in OPERATION mode when decorate_view() on top of @api.method
    """
    api = NinjaAPI()

    @decorate_view(operation_decorator, mode="operation")
    @api.get("/before")
    def dec_before(request):
        return {"message": "test"}

    client = TestClient(api)
    response = client.get("/before")
    assert response.status_code == 200
    assert response.json() == {"message": "test", "operation_decorated": True}


def test_decorator_operation_mode_after_api_method():
    """
    Test decorate_view in OPERATION mode when decorate_view() after @api.method
    """
    api = NinjaAPI()

    @api.get("/after")
    @decorate_view(operation_decorator, mode="operation")
    def dec_after(request):
        return {"message": "test"}

    client = TestClient(api)
    response = client.get("/after")
    assert response.status_code == 200
    assert response.json() == {"message": "test", "operation_decorated": True}


def test_decorator_view_mode_on_top_of_api_method():
    """
    Test decorate_view in VIEW mode when decorate_view() on top of @api.method
    """
    api = NinjaAPI()

    @decorate_view(view_decorator, mode="view")
    @api.get("/before")
    def dec_before(request):
        return {"message": "test"}

    client = TestClient(api)
    response = client.get("/before")
    assert response.status_code == 200
    assert response["X-View-Decorator"] == "view_decorator"
    assert response.json() == {"message": "test"}


def test_decorator_view_mode_after_api_method():
    """
    Test decorate_view in VIEW mode when decorate_view() after @api.method
    """
    api = NinjaAPI()

    @api.get("/after")
    @decorate_view(view_decorator, mode="view")
    def dec_after(request):
        return {"message": "test"}

    client = TestClient(api)
    response = client.get("/after")
    assert response.status_code == 200
    assert response["X-View-Decorator"] == "view_decorator"
    assert response.json() == {"message": "test"}


def test_multiple_decorators():
    """Test multiple decorators with the same mode"""
    api = NinjaAPI()

    @api.get("/test")
    @decorate_view(operation_decorator, mode="operation")
    @decorate_view(counter_decorator, mode="operation")
    def endpoint(request):
        return {"message": "test"}

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
    assert result["operation_decorated"] is True
    assert result["call_count"] == 2


def test_mix_view_and_operation_decorators():
    """Test mixing VIEW and OPERATION mode decorators"""
    api = NinjaAPI()

    @api.get("/test")
    @decorate_view(view_decorator, mode="view")
    @decorate_view(operation_decorator, mode="operation")
    def endpoint(request):
        return {"message": "test"}

    client = TestClient(api)

    response = client.get("/test")
    assert response.status_code == 200
    assert response["X-View-Decorator"] == "view_decorator"
    assert response.json() == {"message": "test", "operation_decorated": True}


def test_invalid_decorator_mode():
    """Test that invalid decorator mode raises ValueError"""
    api = NinjaAPI()

    with pytest.raises(ValueError, match="Invalid decorator mode"):

        @api.get("/test")
        @decorate_view(operation_decorator, mode="invalid")  # type: ignore
        def endpoint(request):
            return {"message": "test"}
