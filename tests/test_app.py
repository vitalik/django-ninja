import os
from tempfile import NamedTemporaryFile

import pytest
from django.http import FileResponse, HttpResponse

from ninja import NinjaAPI
from ninja.main import ConfigError
from ninja.testing import TestClient

api = NinjaAPI()

client = TestClient(api)

# TODO: check if you add  operation to the same path - it should raise a ConfigError that this path already exist
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


@api.get("/file")
def file_response(request):
    tmp = NamedTemporaryFile(delete=False)
    try:
        with open(tmp.name, "wb") as f:
            f.write(b"this is a file")
        return FileResponse(open(tmp.name, "rb"))
    finally:
        try:
            os.remove(tmp.name)
        except PermissionError:
            pass


@pytest.mark.parametrize(
    # fmt: off
    "method,path,expected_status,expected_data,expected_streaming",
    [
        ("get",    "/",       200, "/", False),
        ("get",    "/get",    200, "this is GET", False),
        ("post",   "/post",   200, "this is POST", False),
        ("put",    "/put",    200, "this is PUT", False),
        ("patch",  "/patch",  200, "this is PATCH", False),
        ("delete", "/delete", 200, "this is DELETE", False),
        ("get",    "/multi",  200, "this is GET", False),
        ("post",   "/multi",  200, "this is POST", False),
        ("patch",  "/multi",  405, b"Method not allowed", False),
        ("get",    "/html",   200, b"html", False),
        ("get",    "/file",   200, b"this is a file", True),
    ],
    # fmt: on
)
def test_method(method, path, expected_status, expected_data, expected_streaming):
    func = getattr(client, method)
    response = func(path)
    assert response.status_code == expected_status
    assert response.streaming == expected_streaming
    try:
        data = response.json()
    except Exception:
        data = response.content
    assert data == expected_data


def test_validates():
    try:
        os.environ["NINJA_SKIP_REGISTRY"] = ""
        with pytest.raises(ConfigError):
            NinjaAPI().urls
    finally:
        os.environ["NINJA_SKIP_REGISTRY"] = "yes"
