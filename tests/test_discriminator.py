from typing import Union

from pydantic import Field
from typing_extensions import Annotated, Literal

from ninja import NinjaAPI, Query, Schema
from ninja.testing import TestClient


class Example1(Schema):
    label: Literal["ONE"]
    value: float


class Example2(Schema):
    label: Literal["TWO"]
    value: int


# Annotated union with discriminator
UnionDiscriminator = Annotated[Union[Example1, Example2], Field(discriminator="label")]

# Regular union without annotation
RegularUnion = Union[Example1, Example2]


api = NinjaAPI()


@api.post("/descr-union")
def create_example(request, payload: UnionDiscriminator):
    return {"data": payload.model_dump(), "type": payload.__class__.__name__}


@api.post("/regular-union")
def create_example_regular(request, payload: RegularUnion):
    return {"data": payload.model_dump(), "type": payload.__class__.__name__}


@api.get("/descr-union")
def get_example(request, payload: UnionDiscriminator = Query(...)):
    return {}


@api.get("/regular-union")
def get_example_regular(request, payload: RegularUnion = Query(...)):
    return {}


client = TestClient(api)


def test_schema():
    schema = api.get_openapi_schema()
    post_detail1 = schema["paths"]["/api/descr-union"]["post"]["requestBody"][
        "content"
    ]["application/json"]["schema"]
    post_detail2 = schema["paths"]["/api/regular-union"]["post"]["requestBody"][
        "content"
    ]["application/json"]["schema"]
    get_detail1 = schema["paths"]["/api/descr-union"]["get"]["parameters"][0]["schema"]
    get_detail2 = schema["paths"]["/api/regular-union"]["get"]["parameters"][0][
        "schema"
    ]

    # First method should have 'discriminator' in OpenAPI api
    assert "discriminator" in post_detail1
    assert "discriminator" in get_detail1
    assert post_detail1["discriminator"] == {
        "mapping": {
            "ONE": "#/components/schemas/Example1",
            "TWO": "#/components/schemas/Example2",
        },
        "propertyName": "label",
    }
    assert get_detail1["discriminator"] == {
        "mapping": {
            "ONE": "#/components/schemas/Example1",
            "TWO": "#/components/schemas/Example2",
        },
        "propertyName": "label",
    }

    # Second method should NOT have 'discriminator'
    assert "discriminator" not in post_detail2
    assert "discriminator" not in get_detail2


def test_annotated_union_with_discriminator():
    # Test Example1
    response = client.post(
        "/descr-union",
        json={"label": "ONE", "value": "42"},
    )
    assert response.status_code == 200
    assert response.json() == {
        "data": {"label": "ONE", "value": 42.0},
        "type": "Example1",
    }

    # Test Example2
    response = client.post(
        "/descr-union",
        json={"label": "TWO", "value": "42"},
    )
    assert response.status_code == 200
    assert response.json() == {
        "data": {"label": "TWO", "value": 42},
        "type": "Example2",
    }


def test_regular_union():
    # Test that regular unions still work
    response = client.post(
        "/regular-union",
        json={"label": "ONE", "value": "2025"},
    )
    assert response.status_code == 200
    assert response.json() == {
        "data": {"label": "ONE", "value": 2025},
        "type": "Example1",
    }

    response = client.post(
        "/regular-union",
        json={"label": "TWO", "value": 123},
    )
    assert response.status_code == 200
    assert response.json() == {
        "data": {"label": "TWO", "value": 123},
        "type": "Example2",
    }


def test_annotated_union_with_discriminator_get():
    # Test Example1
    response = client.get(
        "/descr-union",
        query_params={"label": "ONE", "value": "42"},
    )
    assert response.status_code == 200

    # Test Example2
    response = client.get(
        "/descr-union",
        query_params={"label": "TWO", "value": "42"},
    )
    assert response.status_code == 200


def test_regular_union_get():
    # Test that regular unions still work
    response = client.get(
        "/regular-union",
        query_params={"label": "ONE", "value": "2025"},
    )
    assert response.status_code == 200

    response = client.get(
        "/regular-union",
        query_params={"label": "TWO", "value": 123},
    )
    assert response.status_code == 200
