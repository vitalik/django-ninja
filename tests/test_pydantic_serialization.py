"""
Test for Pydantic model serialization with non-JSON-serializable types.

This test demonstrates a bug where Pydantic models with set fields (and other
non-JSON-serializable types) fail to serialize because ninja calls .model_dump()
instead of .model_dump(mode="json").

The bug is in ninja/responses.py line 24, where it should use:
    return o.model_dump(mode="json")
instead of:
    return o.model_dump()

THE FIX:
--------
In ninja/responses.py, change line 24 in the NinjaJSONEncoder.default() method:

    class NinjaJSONEncoder(DjangoJSONEncoder):
        def default(self, o: Any) -> Any:
            if isinstance(o, BaseModel):
                # OLD (broken): return o.model_dump()
                return o.model_dump(mode="json")  # FIX: Add mode="json"
            if isinstance(o, Url):
                return str(o)
            # ... rest of the method

This ensures Pydantic properly converts non-JSON-serializable types:
- set → list
- UUID → str
- Decimal → float/str
- datetime → str (ISO format)
- etc.
"""

from datetime import datetime
from decimal import Decimal
from typing import Annotated
from uuid import UUID, uuid4

import pytest
from pydantic import BaseModel, Field

from ninja import Router
from ninja.testing import TestClient

router = Router()


class ResponseWithSet(BaseModel):
    """Response model with a set field that needs JSON serialization."""

    tags: Annotated[set[str], Field(description="Product tags")]
    name: str


class ResponseWithComplexTypes(BaseModel):
    """Response with various types needing JSON mode serialization."""

    id: UUID
    price: Decimal
    tags: set[str]
    created_at: datetime


class ResponseWithNestedSet(BaseModel):
    """Response with nested structure containing sets."""

    product_name: str
    categories: set[str]
    related_tags: list[set[str]]


@router.get("/with-set/", response=ResponseWithSet)
def endpoint_with_set(request):
    """Endpoint returning a response with a set field."""
    return ResponseWithSet(tags={"tag1", "tag2", "tag3"}, name="Test Product")


@router.get("/with-complex-types/", response=ResponseWithComplexTypes)
def endpoint_with_complex_types(request):
    """Endpoint returning a response with UUID, Decimal, set, and datetime."""
    return ResponseWithComplexTypes(
        id=UUID("12345678-1234-5678-1234-567812345678"),
        price=Decimal("19.99"),
        tags={"electronics", "gadget", "new"},
        created_at=datetime(2024, 1, 15, 10, 30, 0),
    )


@router.get("/with-nested-set/", response=ResponseWithNestedSet)
def endpoint_with_nested_set(request):
    """Endpoint returning a response with nested sets."""
    return ResponseWithNestedSet(
        product_name="Laptop",
        categories={"electronics", "computers"},
        related_tags=[{"tag1", "tag2"}, {"tag3", "tag4"}],
    )


client = TestClient(router)


def test_set_field_serialization():
    """
    Test that set fields are properly converted to lists during serialization.

    Without mode="json", this fails with:
        TypeError: Object of type set is not JSON serializable
    """
    response = client.get("/with-set/")

    assert response.status_code == 200, response.content

    # Verify the response contains a list (not a set)
    data = response.json()
    assert isinstance(data["tags"], list), "tags should be serialized as a list"
    assert sorted(data["tags"]) == ["tag1", "tag2", "tag3"]
    assert data["name"] == "Test Product"


def test_complex_types_serialization():
    """
    Test that UUID, Decimal, datetime, and set all serialize correctly.

    Without mode="json", this fails because sets are not JSON serializable.
    With mode="json", Pydantic handles all these conversions:
    - UUID → str
    - Decimal → float/str (depending on configuration)
    - set → list
    - datetime → str (ISO format)
    """
    response = client.get("/with-complex-types/")

    assert response.status_code == 200, response.content

    data = response.json()

    # UUID should be serialized as string
    assert isinstance(data["id"], str)
    assert data["id"] == "12345678-1234-5678-1234-567812345678"

    # Decimal should be serialized as number
    assert isinstance(data["price"], (int, float, str))

    # Set should be serialized as list
    assert isinstance(data["tags"], list)
    assert sorted(data["tags"]) == ["electronics", "gadget", "new"]

    # Datetime should be serialized as string
    assert isinstance(data["created_at"], str)


def test_nested_set_serialization():
    """
    Test that nested structures with sets serialize correctly.

    This ensures that mode="json" works recursively for nested structures.
    """
    response = client.get("/with-nested-set/")

    assert response.status_code == 200, response.content

    data = response.json()

    # Top-level set should be list
    assert isinstance(data["categories"], list)
    assert sorted(data["categories"]) == ["computers", "electronics"]

    # Nested sets should also be lists
    assert isinstance(data["related_tags"], list)
    assert len(data["related_tags"]) == 2

    for tag_group in data["related_tags"]:
        assert isinstance(tag_group, list), "Nested sets should be serialized as lists"

    # Verify content (order may vary within sets, so we sort)
    tag_sets = [sorted(tag_group) for tag_group in data["related_tags"]]
    assert sorted(tag_sets) == [["tag1", "tag2"], ["tag3", "tag4"]]


def test_empty_set_serialization():
    """Test that empty sets are serialized as empty lists."""

    @router.get("/with-empty-set/", response=ResponseWithSet)
    def endpoint_with_empty_set(request):
        return ResponseWithSet(tags=set(), name="Empty Tags")

    response = client.get("/with-empty-set/")

    assert response.status_code == 200
    data = response.json()

    assert isinstance(data["tags"], list)
    assert data["tags"] == []
    assert data["name"] == "Empty Tags"


@pytest.mark.parametrize(
    "tags,expected_sorted",
    [
        ({"a", "b", "c"}, ["a", "b", "c"]),
        ({"zebra", "apple", "banana"}, ["apple", "banana", "zebra"]),
        ({"1", "2", "3"}, ["1", "2", "3"]),
        (set(), []),
    ],
)
def test_set_serialization_various_values(tags, expected_sorted):
    """Test set serialization with various input values."""

    @router.get("/with-parametrized-set/", response=ResponseWithSet)
    def endpoint_with_parametrized_set(request):
        return ResponseWithSet(tags=tags, name="Test")

    response = client.get("/with-parametrized-set/")

    assert response.status_code == 200
    data = response.json()

    assert isinstance(data["tags"], list)
    assert sorted(data["tags"]) == expected_sorted
