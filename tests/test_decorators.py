from functools import wraps
from typing import List

from ninja import NinjaAPI
from ninja.decorators import decorate_view
from ninja.pagination import paginate
from ninja.testing import TestClient


def some_decorator(view_func):
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        response = view_func(request, *args)
        response["X-Decorator"] = "some_decorator"
        return response

    return wrapper


def test_decorator_before():
    api = NinjaAPI()

    @decorate_view(some_decorator)
    @api.get("/before")
    def dec_before(request):
        return 1

    client = TestClient(api)
    response = client.get("/before")
    assert response.status_code == 200
    assert response["X-Decorator"] == "some_decorator"


def test_decorator_after():
    api = NinjaAPI()

    @api.get("/after")
    @decorate_view(some_decorator)
    def dec_after(request):
        return 1

    client = TestClient(api)
    response = client.get("/after")
    assert response.status_code == 200
    assert response["X-Decorator"] == "some_decorator"


def test_decorator_multiple():
    api = NinjaAPI()

    @api.get("/multi", response=List[int])
    @decorate_view(some_decorator)
    @paginate
    def dec_multi(request):
        return [1, 2, 3, 4]

    client = TestClient(api)
    response = client.get("/multi")
    assert response.status_code == 200
    assert response.json() == {"count": 4, "items": [1, 2, 3, 4]}
    assert response["X-Decorator"] == "some_decorator"


class DependencyService:
    def get_data(self):
        return "injected_data"


def inject_dependency(view_func):
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        kwargs["injected_service"] = DependencyService()
        return view_func(request, *args, **kwargs)

    wrapper._ninja_ignore_args = ["injected_service"]
    return wrapper


def test_ninja_ignore_args_integration():
    """Integration test for _ninja_ignore_args functionality."""
    api = NinjaAPI()

    @api.get("/test-ignore/{item_id}")
    @inject_dependency
    def test_view(
        request, item_id: int, query_param: str, injected_service: DependencyService
    ):
        data = injected_service.get_data()
        return {"item_id": item_id, "query_param": query_param, "injected_data": data}

    # Test that the endpoint works correctly
    client = TestClient(api)
    response = client.get("/test-ignore/123?query_param=test")
    assert response.status_code == 200
    assert response.json() == {
        "item_id": 123,
        "query_param": "test",
        "injected_data": "injected_data",
    }

    # Test that injected_service is not in the OpenAPI schema
    schema = api.get_openapi_schema()
    parameters = schema["paths"]["/api/test-ignore/{item_id}"]["get"]["parameters"]

    # Should have item_id (path) and query_param (query), but not injected_service
    param_names = [p["name"] for p in parameters]
    assert "item_id" in param_names
    assert "query_param" in param_names
    assert "injected_service" not in param_names
