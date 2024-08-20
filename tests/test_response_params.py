from typing import Optional

from ninja import NinjaAPI, Schema
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
