from typing import List, Optional

import pytest
from pydantic import BeforeValidator
from typing_extensions import Annotated

from ninja import Field, NinjaAPI, Schema
from ninja.patch_dict import PatchDict
from ninja.testing import TestClient

api = NinjaAPI()

client = TestClient(api)


class SomeSchema(Schema):
    name: str
    age: int
    category: Optional[str] = None
    identifier: str = Field(max_length=32)
    code: Annotated[str, BeforeValidator(lambda v: v.strip()), Field(min_length=2)]


class OtherSchema(SomeSchema):
    other: str
    category: Optional[List[str]] = None


@api.patch("/patch")
def patch(request, payload: PatchDict[SomeSchema]):
    return {"payload": payload, "type": str(type(payload))}


@api.patch("/patch-inherited")
def patch_inherited(request, payload: PatchDict[OtherSchema]):
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


@pytest.mark.parametrize("input", [{"identifier": "0" * 100}, {"code": "0"}])
def test_patch_calls_bad_request(input: dict):
    response = client.patch("/patch", json=input)
    assert response.status_code == 422


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
            "identifier": {
                "anyOf": [
                    {"maxLength": 32, "type": "string"},
                    {"type": "null"},
                ],
                "title": "Identifier",
            },
            "code": {
                "anyOf": [{"type": "string"}, {"type": "null"}],
                "minLength": 2,
                "title": "Code",
            },
        },
    }


def test_patch_inherited():
    input = {"other": "any", "category": ["cat1", "cat2"]}
    expected_output = {"payload": input, "type": "<class 'dict'>"}

    response = client.patch("/patch-inherited", json=input)
    assert response.json() == expected_output


def test_inherited_schema():
    "Checking that json schema properties for inherithed schemas are ok"
    schema = api.get_openapi_schema()
    assert schema["components"]["schemas"]["OtherSchemaPatch"] == {
        "title": "OtherSchemaPatch",
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
            "identifier": {
                "anyOf": [
                    {"maxLength": 32, "type": "string"},
                    {"type": "null"},
                ],
                "title": "Identifier",
            },
            "code": {
                "anyOf": [{"type": "string"}, {"type": "null"}],
                "minLength": 2,
                "title": "Code",
            },
            "other": {
                "anyOf": [{"type": "string"}, {"type": "null"}],
                "title": "Other",
            },
            "category": {
                "anyOf": [
                    {
                        "items": {
                            "type": "string",
                        },
                        "type": "array",
                    },
                    {"type": "null"},
                ],
                "title": "Category",
            },
        },
    }
