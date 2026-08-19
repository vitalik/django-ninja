from typing import List, Optional

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


class OtherSchema(SomeSchema):
    other: str
    category: Optional[List[str]] = None


class TagSchema(Schema):
    name: str


class MultiRefSchema(Schema):
    label: str
    primary: Optional[List[TagSchema]] = None
    secondary: Optional[List[TagSchema]] = None


@api.patch("/patch-multi-ref")
def patch_multi_ref(request, payload: PatchDict[MultiRefSchema]):
    return {"payload": payload, "type": str(type(payload))}


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


def test_patch_inherited():
    input = {"other": "any", "category": ["cat1", "cat2"]}
    expected_output = {"payload": input, "type": "<class 'dict'>"}

    response = client.patch("/patch-inherited", json=input)
    assert response.json() == expected_output


def test_patch_repeated_sub_model():
    # a sub-model referenced by more than one field must not break schema
    # generation (the wrapped model's schema uses $ref definitions).
    input = {"label": "x", "primary": [{"name": "a"}]}
    expected_output = {"payload": input, "type": "<class 'dict'>"}

    response = client.patch("/patch-multi-ref", json=input)
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
