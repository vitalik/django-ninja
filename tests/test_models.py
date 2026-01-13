from typing import List, Union

import pytest
from pydantic import BaseModel

from ninja import Form, NinjaAPI, Query, Router
from ninja.errors import ConfigError
from ninja.testing import TestClient


class SomeModel(BaseModel):
    i: int
    s: str
    f: float
    n: int | None = None


class OtherModel(BaseModel):
    x: int
    y: int


class SelfReference(BaseModel):
    a: int = 123
    sibling: "SelfReference" = None


SelfReference.model_rebuild()


# Union type models for testing union type handling
class PetSchema(BaseModel):
    nicknames: list[str]


class PersonSchema(BaseModel):
    name: str
    age: int
    pet: PetSchema | None = None


class NestedUnionModel(BaseModel):
    nested_field: Union[PersonSchema, None] = None
    simple_field: str = "default"


class ComplexUnionModel(BaseModel):
    # Union field with pydantic models
    model_union: Union[SomeModel, OtherModel] | None = None
    # Simple union field
    simple_union: Union[str, int] = "default"


# Model with non-optional union of pydantic models
class MultiModelUnion(BaseModel):
    # Union of multiple pydantic models without None -
    models: Union[SomeModel, OtherModel]  # No default, no None


router = Router()


@router.post("/test1")
def view1(request, some: SomeModel):
    assert isinstance(some, SomeModel)
    return some


@router.post("/test2")
def view2(request, some: SomeModel, other: OtherModel):
    assert isinstance(some, SomeModel)
    assert isinstance(other, OtherModel)
    return {"some": some, "other": other}


@router.post("/test3")
def view3(request, some: "SomeModel"):
    assert isinstance(some, SomeModel)
    return some


@router.post("/test_form")
def view4(request, form: OtherModel = Form(...)):
    assert isinstance(form, OtherModel)
    return form


@router.post("/test_query")
def view4query(request, q: OtherModel = Query(...)):
    assert isinstance(q, OtherModel)
    return q


@router.post("/selfref")
def view5(request, obj: SelfReference):
    assert isinstance(obj, SelfReference)
    return obj


@router.post("/model-default")
def view6(request, obj: OtherModel = None):
    assert isinstance(obj, (OtherModel, None.__class__))
    return obj


@router.post("/model-default2")
def view7(request, obj: OtherModel = OtherModel(x=1, y=1)):
    assert isinstance(obj, OtherModel)
    return obj


# Union type test views
@router.post("/test-union-query")
def view_union_query(request, person: PersonSchema = Query(...)):
    return person


@router.post("/test-union-body")
def view_union_body(request, union_body: Union[SomeModel, OtherModel]):
    return union_body


@router.post("/test-optional-union")
def view_optional_union(request, optional_model: Union[SomeModel, None] = Query(None)):
    if optional_model is None:
        return {"result": "none"}
    return {"result": optional_model}


@router.post("/test-nested-union")
def view_nested_union(request, data: NestedUnionModel):
    return data.model_dump()


@router.post("/test-complex-union")
def view_complex_union(request, data: ComplexUnionModel = Query(...)):
    return data


# Test direct union parameter to cover _model_flatten_map
@router.post("/test-direct-union")
def view_direct_union(request, model: Union[SomeModel, OtherModel] = Query(...)):
    return model


# Test union of pydantic models
@router.post("/test-multi-model-union")
def view_multi_model_union(request, data: MultiModelUnion):
    return data.model_dump()


@router.post("/test-union-with-none")
def view_union_with_none(request, optional: Union[str, None] = Query(None)):
    """Test Union[str, None]"""
    return {"optional": optional}


class CollectionUnionModel(BaseModel):
    items: List[str]
    nested: Union[SomeModel, None] = None


@router.post("/test-collection-union")
def view_collection_union(request, data: CollectionUnionModel):
    return data.model_dump()


client = TestClient(router)


@pytest.mark.parametrize(
    # fmt: off
    "path,kwargs,expected_response",
    [
        (
            "/test1",
            dict(json={"i": "1", "s": "foo", "f": "1.1"}),
            {"i": 1, "s": "foo", "f": 1.1, "n": None},
        ),
        (
            "/test1",
            dict(json={"i": "1", "s": "foo", "f": "1.1", "n": 42}),
            {"i": 1, "s": "foo", "f": 1.1, "n": 42},
        ),
        (
            "/test2",
            dict(
                json={
                    "some": {"i": "1", "s": "foo", "f": "1.1"},
                    "other": {"x": 1, "y": 2},
                }
            ),
            {
                "some": {"i": 1, "s": "foo", "f": 1.1, "n": None},
                "other": {"x": 1, "y": 2},
            },
        ),
        (
            "/test3",
            dict(json={"i": "1", "s": "foo", "f": "1.1"}),
            {"i": 1, "s": "foo", "f": 1.1, "n": None},
        ),
        (
            "/test_form",
            dict(data={"x": "10000", "y": "20000"}),
            {"x": 10000, "y": 20000},
        ),
        (
            "/test_query?x=5&y=6",
            dict(json=None),
            {"x": 5, "y": 6},
        ),
        (
            "/selfref",
            dict(json={"a": "1"}),
            {"a": 1, "sibling": None},
        ),
        (
            "/selfref",
            dict(json={"a": "1", "sibling": {"a": 2}}),
            {"a": 1, "sibling": {"a": 2, "sibling": None}},
        ),
        (
            "model-default",
            dict(json=None),
            None,
        ),
        (
            "model-default2",
            dict(json=None),
            {"x": 1, "y": 1},
        ),
        (
            "/test-union-query?name=John&age=30",
            dict(json=None),
            {"name": "John", "age": 30, "pet": None},
        ),
        (
            "/test-union-body",
            dict(json={"i": 1, "s": "test", "f": 1.5}),
            {"i": 1, "s": "test", "f": 1.5, "n": None},
        ),
        (
            "/test-direct-union?i=1&s=test&f=1.5",
            dict(json=None),
            {"i": 1, "s": "test", "f": 1.5, "n": None},
        ),
        (
            "/test-union-with-none",
            dict(json=None),
            {"optional": None},
        ),
        (
            "/test-union-with-none?optional=test",
            dict(json=None),
            {"optional": "test"},
        ),
        # Test collection union model
        (
            "/test-collection-union",
            dict(json={"items": ["a", "b"], "nested": None}),
            {"items": ["a", "b"], "nested": None},
        ),
        (
            "/test-collection-union",
            dict(json={"items": ["x"], "nested": {"i": 5, "s": "test", "f": 2.0}}),
            {"items": ["x"], "nested": {"i": 5, "s": "test", "f": 2.0, "n": None}},
        ),
        (
            "/test-multi-model-union",
            dict(json={"models": {"i": 1, "s": "test", "f": 1.5}}),
            {"models": {"i": 1, "s": "test", "f": 1.5, "n": None}},
        ),
        (
            "/test-optional-union",
            dict(json=None),
            {"result": "none"},
        ),
        (
            "/test-nested-union",
            dict(json={"nested_field": None, "simple_field": "test"}),
            {"nested_field": None, "simple_field": "test"},
        ),
        (
            "/test-complex-union?simple_union=42",
            dict(json=None),
            {"model_union": None, "simple_union": "42"},
        ),
    ],
    # fmt: on
)
def test_models(path, kwargs, expected_response):
    response = client.post(path, **kwargs)
    assert response.status_code == 200, response.content
    assert response.json() == expected_response


def test_invalid_body():
    response = client.post("/test1", body="invalid")
    assert response.status_code == 400, response.content
    assert response.json() == {
        "detail": "Cannot parse request body",
    }


def test_union_query_name_collision():
    """Test that duplicate union parameter names with Query(None) raise ConfigError."""

    with pytest.raises(ConfigError, match=r"Duplicated name.*person"):
        api = NinjaAPI()
        router_test = Router()

        @router_test.post("/collision-test")
        def collision_endpoint(
            person1: Union[PersonSchema, None] = Query(None, alias="person"),
            person2: Union[PersonSchema, None] = Query(None, alias="person"),
        ):
            return {"result": "should not reach here"}

        api.add_router("/test", router_test)


def test_union_with_none_body_param():
    """Test Union[Model, None] parameter"""

    test_router = Router()

    @test_router.post("/test-union-none-body")
    def test_union_none_body(request, data: Union[SomeModel, None]):
        return data.model_dump() if data else {"result": "none"}

    # Verify the router was created successfully and has one registered operation
    assert len(test_router.path_operations) == 1
