import pytest
import django
from django.http import Http404
from ninja import NinjaAPI
from client import NinjaClient, NinjaAsyncClient


api = NinjaAPI()


class CustomException(Exception):
    pass


@api.exception_handler(CustomException)
def on_custom_error(request, exc):
    return api.create_response(request, {"custom": True}, status=422)


@api.get("/error/{code}")
def err_thrower(request, code: str):
    if code == "base":
        raise RuntimeError("test")
    if code == "404":
        raise Http404("test")
    if code == "custom":
        raise CustomException("test")


client = NinjaClient(api)


def test_default_handler(settings):
    settings.DEBUG = True

    response = client.get("/error/base")
    assert response.status_code == 500
    assert b"RuntimeError: test" in response.content

    settings.DEBUG = False
    with pytest.raises(RuntimeError):
        response = client.get("/error/base")


def test_exceptions():
    response = client.get("/error/404")
    assert response.status_code == 404
    assert response.json() == {"code": 404, "message": "Not Found"}

    response = client.get("/error/custom")
    assert response.status_code == 422
    assert response.json() == {"custom": True}


@pytest.mark.skipif(django.VERSION < (3, 1), reason="requires django 3.1 or higher")
@pytest.mark.asyncio
async def test_asyncio_exceptions():
    api = NinjaAPI()

    @api.get("/error")
    async def thrower(request):
        raise Http404("test")

    client = NinjaAsyncClient(api)
    response = await client.get("/error")
    assert response.status_code == 404


def test_no_handlers():
    api = NinjaAPI()
    api._exception_handlers = {}

    @api.get("/error")
    def thrower(request):
        raise RuntimeError("test")

    client = NinjaClient(api)

    with pytest.raises(RuntimeError):
        client.get("/error")
