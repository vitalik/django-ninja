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
