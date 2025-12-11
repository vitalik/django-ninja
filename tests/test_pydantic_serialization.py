"""Test Pydantic model serialization with non-JSON-serializable types."""

from datetime import datetime
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel

from ninja import Router
from ninja.testing import TestClient

router = Router()


class ResponseWithSet(BaseModel):
    tags: set[str]
    name: str


class ResponseWithComplexTypes(BaseModel):
    id: UUID
    price: Decimal
    tags: set[str]
    created_at: datetime


@router.get("/with-set/", response=ResponseWithSet)
def endpoint_with_set(request):
    return ResponseWithSet(tags={"tag1", "tag2", "tag3"}, name="Test Product")


@router.get("/with-complex-types/", response=ResponseWithComplexTypes)
def endpoint_with_complex_types(request):
    return ResponseWithComplexTypes(
        id=UUID("12345678-1234-5678-1234-567812345678"),
        price=Decimal("19.99"),
        tags={"electronics", "gadget", "new"},
        created_at=datetime(2024, 1, 15, 10, 30, 0),
    )


client = TestClient(router)


def test_set_field_serialization():
    """
    Test that set fields serialize to JSON properly.

    Fix: In ninja/responses.py line 24, change:
        return o.model_dump()
    to:
        return o.model_dump(mode="json")
    """
    response = client.get("/with-set/")

    assert response.status_code == 200
    data = response.json()
    assert isinstance(data["tags"], list)
    assert sorted(data["tags"]) == ["tag1", "tag2", "tag3"]


def test_complex_types_serialization():
    """Test that UUID, Decimal, set, and datetime all serialize correctly with mode="json"."""
    response = client.get("/with-complex-types/")

    assert response.status_code == 200
    data = response.json()

    assert isinstance(data["id"], str)
    assert isinstance(data["tags"], list)
    assert sorted(data["tags"]) == ["electronics", "gadget", "new"]
