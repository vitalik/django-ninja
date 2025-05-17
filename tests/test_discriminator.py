from typing import Literal, Union
from typing_extensions import Annotated

from pydantic import Field
from ninja import NinjaAPI, Schema
from ninja.testing import TestClient


class Example1(Schema):
    label: Literal["ONE"]
    val1: str


class Example2(Schema):
    label: Literal["TWO"]
    val2: int


# Annotated union with discriminator
ExampleUnion = Annotated[Union[Example1, Example2], Field(discriminator="label")]

# Regular union without annotation
RegularUnion = Union[Example1, Example2]


api = NinjaAPI()


@api.post("/examples")
def create_example(request, payload: ExampleUnion):
    return payload.model_dump()


@api.post("/regular-union")
def create_example_regular(request, payload: RegularUnion):
    return payload.model_dump()


client = TestClient(api)


def test_annotated_union_with_discriminator():
    # Test Example1
    response = client.post(
        "/examples",
        json={"label": "ONE", "val1": "test"},
    )
    assert response.status_code == 200
    assert response.json() == {"label": "ONE", "val1": "test"}

    # Test Example2
    response = client.post(
        "/examples",
        json={"label": "TWO", "val2": 123},
    )
    assert response.status_code == 200
    assert response.json() == {"label": "TWO", "val2": 123}


def test_regular_union():
    # Test that regular unions still work
    response = client.post(
        "/regular-union",
        json={"label": "ONE", "val1": "test"},
    )
    assert response.status_code == 200
    assert response.json() == {"label": "ONE", "val1": "test"}

    response = client.post(
        "/regular-union",
        json={"label": "TWO", "val2": 123},
    )
    assert response.status_code == 200
    assert response.json() == {"label": "TWO", "val2": 123}
