import os
import pytest
from ninja import NinjaAPI
from ninja.main import ConfigError
from django.http import HttpResponse
from client import NinjaClient


api = NinjaAPI()


# TODO: check if you add  operaiotn to the same path - it should raise a ConfigError that this path already exist
# make sure to check how this will work with versioning
# and also check what will happen if you add same path in different routers
#  api.add_router("", router1)
#  api.add_router("", router2)
# and both routers have same path defined


@api.get("")
def emptypath(request):
    return "/"


@api.get("/get")
def get(request):
    return f"this is {request.method}"


@api.post("/post")
def post(request):
    return f"this is {request.method}"


@api.put("/put")
def put(request):
    return f"this is {request.method}"


@api.patch("/patch")
def patch(request):
    return f"this is {request.method}"


@api.delete("/delete")
def delete(request):
    return f"this is {request.method}"


@api.api_operation(["GET", "POST"], "/multi")
def multiple(request):
    return f"this is {request.method}"


@api.get("/html")
def html(request):
    return HttpResponse("html")


client = NinjaClient(api)


@pytest.mark.parametrize(
    # fmt: off
    "method,path,expected_status,expected_data",
    [
        ("get",    "/",       200, "/"),
        ("get",    "/get",    200, "this is GET"),
        ("post",   "/post",   200, "this is POST"),
        ("put",    "/put",    200, "this is PUT"),
        ("patch",  "/patch",  200, "this is PATCH"),
        ("delete", "/delete", 200, "this is DELETE"),
        ("get",    "/multi",  200, "this is GET"),
        ("post",   "/multi",  200, "this is POST"),
        ("patch",  "/multi",  405, b"Method not allowed"),
        ("get",    "/html",   200, b"html"),
    ],
    # fmt: on
)
def test_method(method, path, expected_status, expected_data):
    func = getattr(client, method)
    response = func(path)
    assert response.status_code == expected_status
    try:
        data = response.json()
    except Exception:
        data = response.content
    assert data == expected_data


def test_validates():
    api1 = NinjaAPI()
    try:
        os.environ["NINJA_SKIP_REGISTRY"] = ""
        with pytest.raises(ConfigError):
            api2 = NinjaAPI()
    finally:
        os.environ["NINJA_SKIP_REGISTRY"] = "yes"
