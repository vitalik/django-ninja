from typing import List
from unittest.mock import Mock

import pytest
from django.http import HttpRequest

from ninja import NinjaAPI, Query, Router
from ninja.errors import ConfigError
from ninja.testing import TestClient

api = NinjaAPI()


@api.post("/no-request")
def no_request():
    return {"result": None}


@api.post("/no-request-args")
def no_request_args(*args):
    assert isinstance(args[0], Mock)
    assert args[0].COOKIES == {}
    return {"result": len(args)}


@api.post("/request")
def just_request(request):
    assert request.COOKIES == {}
    return {"result": None}


@api.post("/request-args")
def request_args(request, *args):
    assert request.COOKIES == {}
    assert len(args) == 0
    return {"result": None}


@api.post("/request-arg-args")
def request_arg_args(request: HttpRequest, arg, *args):
    assert request.COOKIES == {}
    assert len(args) == 0
    return {"result": arg}


@api.post("/not-named-request-typed-arg")
def not_named_request_typed_arg(not_named_request: HttpRequest, request):
    assert not_named_request.COOKIES == {}
    return {"result": request}


@api.post("/no-request-arg-default")
def no_request_arg_default(arg: int = 3):
    return {"result": arg}


@api.post("/no-request-arg-path/{arg}/")
def no_request_arg_path(arg):
    return {"result": arg}


@api.post("/no-request-arg-typed")
def no_request_arg_typed(arg: int):
    return {"result": arg}


@api.post("/no-request-arg-collection")
def no_request_arg_collection(arg: List[int] = Query(...)):
    return {"result": arg}


@pytest.mark.parametrize(
    "url, expected",
    (
        ("/no-request", {"result": None}),
        ("/no-request-args", {"result": 1}),
        ("/request", {"result": None}),
        ("/request-args", {"result": None}),
        ("/request-arg-args?arg=1", {"result": "1"}),
        ("/not-named-request-typed-arg?request=2", {"result": "2"}),
        ("/no-request-arg-default", {"result": 3}),
        ("/no-request-arg-path/4/", {"result": "4"}),
        ("/no-request-arg-typed?arg=5", {"result": 5}),
        ("/no-request-arg-collection?arg=6&arg=7", {"result": [6, 7]}),
    ),
)
def test_request_param(url, expected):
    client = TestClient(api)
    assert client.post(url).json() == expected


def test_request_param_problems():
    test_router = Router()
    with pytest.raises(ConfigError, match="'request' param cannot have a default"):

        @test_router.get("/path")
        def request_default(request=2):
            pass

    match = "'request' param type 'int' is not a subclass of django.http.HttpRequest"
    with pytest.warns(UserWarning, match=match):

        @test_router.get("/path")
        def request_wrong_type(request: int):
            pass
