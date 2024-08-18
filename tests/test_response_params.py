from typing import Optional

from ninja import NinjaAPI, Router, Schema
from ninja.testing import TestClient

api = NinjaAPI()


class SomeResponse(Schema):
    field1: Optional[int] = 1
    field2: Optional[str] = "default value"
    field3: Optional[int] = None


@api.get("/test-no-params", response=SomeResponse)
def op_no_params(request):
    return {}  # should set defaults from schema


@api.get("/test-unset", response=SomeResponse, exclude_unset=True)
def op_exclude_unset(request):
    return {"field3": 10}


@api.get("/test-defaults", response=SomeResponse, exclude_defaults=True)
def op_exclude_defaults(request):
    # changing only field1
    return {"field1": 3, "field2": "default value"}


@api.get("/test-none", response=SomeResponse, exclude_none=True)
def op_exclude_none(request):
    # setting field1 to None to exclude
    return {"field1": None, "field2": "default value"}


router_exc_unset = Router(operation_defaults={"exclude_unset": True})


@router_exc_unset.get("/r1-test-unset", response=SomeResponse, exclude_unset=True)
def r1_op_exclude_unset(request):
    return {"field3": 10}


router_exc_defaults = Router(operation_defaults={"exclude_defaults": True})


@router_exc_defaults.get("/r2-test-defaults", response=SomeResponse)
def r2_op_exclude_defaults(request):
    # changing only field1
    return {"field1": 3, "field2": "default value"}


router_exc_none = Router(operation_defaults={"exclude_none": True})


@router_exc_none.get("/r3-test-none", response=SomeResponse)
def r3_op_exclude_none(request):
    # setting field1 to None to exclude
    return {"field1": None, "field2": "default value"}


api.add_router("", router_exc_unset)
api.add_router("", router_exc_defaults)
api.add_router("", router_exc_none)


client = TestClient(api)


def test_arguments():
    assert client.get("/test-no-params").json() == {
        "field1": 1,
        "field2": "default value",
        "field3": None,
    }
    assert client.get("/test-unset").json() == {"field3": 10}
    assert client.get("/test-defaults").json() == {"field1": 3}
    assert client.get("/test-none").json() == {"field2": "default value"}

    assert client.get("/r1-test-unset").json() == {"field3": 10}
    assert client.get("/r2-test-defaults").json() == {"field1": 3}
    assert client.get("/r3-test-none").json() == {"field2": "default value"}
