from typing import Optional

import pytest

from ninja import NinjaAPI, Schema
from ninja.patch_dict import PatchDict
from ninja.testing import TestClient

api = NinjaAPI()

client = TestClient(api)


class SomeSchema(Schema):
    name: str
    age: int
    category: Optional[str] = None


@api.patch("/patch")
def patch(request, payload: PatchDict[SomeSchema]):
    return {"payload": payload, "type": str(type(payload))}


@pytest.mark.parametrize(
    "input,output",
    [
        ({"name": "foo"}, {"name": "foo"}),
        ({"age": "1"}, {"age": 1}),
        ({}, {}),
        ({"wrong_param": 1}, {}),
        ({"age": None}, {"age": None}),
    ],
)
def test_patch_calls(input: dict, output: dict):
    response = client.patch("/patch", json=input)
    assert response.json() == {"payload": output, "type": "<class 'dict'>"}


def test_schema():
    "Checking that json schema properties are all optional"
    schema = api.get_openapi_schema()
    assert schema["components"]["schemas"]["SomeSchemaPatch"] == {
        "title": "SomeSchemaPatch",
        "type": "object",
        "properties": {
            "name": {
                "anyOf": [{"type": "string"}, {"type": "null"}],
                "title": "Name",
            },
            "age": {
                "anyOf": [{"type": "integer"}, {"type": "null"}],
                "title": "Age",
            },
            "category": {
                "anyOf": [{"type": "string"}, {"type": "null"}],
                "title": "Category",
            },
        },
    }
