from typing import List

import pytest
from django.http import HttpRequest

from ninja import NinjaAPI, Query
from ninja.testing import TestClient

api = NinjaAPI()


@api.post("/no-request")
def no_request():
    return {"result": None}


@api.post("/no-request-args")
def no_request_args(*args):
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


@api.post("/not-named-request-typed-arg-2")
def not_named_request_typed_arg2(arg, r: HttpRequest):
    assert r.COOKIES == {}
    return {"result": arg}


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


@api.post("/request-req-collection")
def request_req_collection(request: List[int] = Query(...)):
    return {"result": request}


@api.post("/request-int")
def request_int(request: int):
    return {"result": request}


@api.post("/request-body")
def request_body(request: List[int] = []):
    return {"result": request}


@api.post("/request-default")
def request_default(request=2):
    return {"result": request}


@pytest.mark.parametrize(
    "url, expected",
    (
        ("/no-request", {"result": None}),
        ("/no-request-args", {"result": 0}),
        ("/request", {"result": None}),
        ("/request-args", {"result": None}),
        ("/request-arg-args?arg=1", {"result": "1"}),
        ("/not-named-request-typed-arg?request=2", {"result": "2"}),
        ("/not-named-request-typed-arg-2?arg=3", {"result": "3"}),
        ("/no-request-arg-default", {"result": 3}),
        ("/no-request-arg-path/4/", {"result": "4"}),
        ("/no-request-arg-typed?arg=5", {"result": 5}),
        ("/no-request-arg-collection?arg=6&arg=7", {"result": [6, 7]}),
        ("/request-req-collection?request=8&request=9", {"result": [8, 9]}),
        ("/request-int?request=10", {"result": 10}),
        ("/request-body", {"result": []}),
        ("/request-default", {"result": 2}),
        ("/request-default?request=1", {"result": 1}),
    ),
)
def test_request_param(url, expected):
    client = TestClient(api)
    assert client.post(url).json() == expected
