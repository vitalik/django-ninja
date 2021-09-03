import django
import pytest
from django.http import Http404

from ninja import NinjaAPI, Schema
from ninja.testing import TestAsyncClient, TestClient

api = NinjaAPI()


class CustomException(Exception):
    pass


@api.exception_handler(CustomException)
def on_custom_error(request, exc):
    return api.create_response(request, {"custom": True}, status=422)


class Payload(Schema):
    test: int


@api.post("/error/{code}")
def err_thrower(request, code: str, payload: Payload = None):
    if code == "base":
        raise RuntimeError("test")
    if code == "404":
        raise Http404("test")
    if code == "custom":
        raise CustomException("test")


client = TestClient(api)


def test_default_handler(settings):
    settings.DEBUG = True

    response = client.post("/error/base")
    assert response.status_code == 500
    assert b"RuntimeError: test" in response.content

    response = client.post("/error/404")
    assert response.status_code == 404
    assert response.json() == {"detail": "Not Found: test"}

    response = client.post("/error/custom", body="invalid_json")
    assert response.status_code == 400
    assert response.json() == {
        "detail": "Cannot parse request body (Expecting value: line 1 column 1 (char 0))",
    }

    settings.DEBUG = False
    with pytest.raises(RuntimeError):
        response = client.post("/error/base")

    response = client.post("/error/custom", body="invalid_json")
    assert response.status_code == 400
    assert response.json() == {"detail": "Cannot parse request body"}


@pytest.mark.parametrize(
    "route,status_code,json",
    [
        ("/error/404", 404, {"detail": "Not Found"}),
        ("/error/custom", 422, {"custom": True}),
    ],
)
def test_exceptions(route, status_code, json):
    response = client.post(route)
    assert response.status_code == status_code
    assert response.json() == json


@pytest.mark.skipif(django.VERSION < (3, 1), reason="requires django 3.1 or higher")
@pytest.mark.asyncio
async def test_asyncio_exceptions():
    api = NinjaAPI()

    @api.get("/error")
    async def thrower(request):
        raise Http404("test")

    client = TestAsyncClient(api)
    response = await client.get("/error")
    assert response.status_code == 404


def test_no_handlers():
    api = NinjaAPI()
    api._exception_handlers = {}

    @api.get("/error")
    def thrower(request):
        raise RuntimeError("test")

    client = TestClient(api)

    with pytest.raises(RuntimeError):
        client.get("/error")
