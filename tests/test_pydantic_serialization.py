"""Test Pydantic model serialization with set fields."""

from pydantic import BaseModel

from ninja import Router
from ninja.testing import TestClient

router = Router()


class ResponseWithSet(BaseModel):
    tags: set[str]
    name: str


@router.get("/with-set/", response=ResponseWithSet)
def endpoint_with_set(request):
    return ResponseWithSet(tags={"tag1", "tag2", "tag3"}, name="Test Product")


client = TestClient(router)


def test_set_field_serialization():
    """Test that set fields serialize correctly."""
    response = client.get("/with-set/")

    assert response.status_code == 200
    data = response.json()
    assert isinstance(data["tags"], list)
    assert sorted(data["tags"]) == ["tag1", "tag2", "tag3"]
