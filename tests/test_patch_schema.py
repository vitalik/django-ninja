from typing import Optional, cast

import pytest
from pydantic import BaseModel, ValidationError

from ninja import NinjaAPI, Schema
from ninja.patch_schema import PatchedModel, PatchSchema
from ninja.testing import TestClient


class UserSchema(BaseModel):
    name: str
    email: str
    age: int
    avatar_url: Optional[str] = None


class UserSchemaWithDefault(BaseModel):
    name: str = "Default"
    email: str
    age: int
    avatar_url: Optional[str] = None


def test_patch_schema_basic():
    PatchUserSchema = PatchSchema[UserSchema]

    # Test empty initialization
    patch_data = cast(PatchedModel, PatchUserSchema())
    assert patch_data.model_dump() == {}

    # Test field initialization
    patch_data = cast(PatchedModel, PatchUserSchema(name="New Name"))
    assert patch_data.model_dump() == {"name": "New Name"}

    # Test multiple fields
    patch_data = cast(
        PatchedModel, PatchUserSchema(name="New Name", email="new@example.com")
    )
    assert patch_data.model_dump() == {"name": "New Name", "email": "new@example.com"}


def test_patch_schema_with_optional_fields():
    PatchUserSchema = PatchSchema[UserSchema]

    # Test setting optional field to None
    patch_data = cast(PatchedModel, PatchUserSchema(avatar_url=None))
    assert patch_data.model_dump() == {"avatar_url": None}

    # Test setting optional field to value
    patch_data = cast(
        PatchedModel, PatchUserSchema(avatar_url="https://example.com/avatar.png")
    )
    assert patch_data.model_dump() == {"avatar_url": "https://example.com/avatar.png"}


def test_patch_schema_none_validation():
    PatchUserSchema = PatchSchema[UserSchema]

    # Non-optional fields should not allow None
    with pytest.raises(ValidationError) as exc_info:
        PatchUserSchema(name=None)

    assert "Field 'name' cannot be None" in str(exc_info.value)

    with pytest.raises(ValidationError) as exc_info:
        PatchUserSchema(email=None)

    assert "Field 'email' cannot be None" in str(exc_info.value)


def test_patch_schema_with_defaults():
    PatchUserSchemaWithDefault = PatchSchema[UserSchemaWithDefault]

    # Default values should not be included in the output unless explicitly set
    patch_data = cast(PatchedModel, PatchUserSchemaWithDefault())
    assert patch_data.model_dump() == {}

    patch_data = cast(PatchedModel, PatchUserSchemaWithDefault(name="Custom Name"))
    assert patch_data.model_dump() == {"name": "Custom Name"}


# API integration tests
api = NinjaAPI()
client = TestClient(api)


class UserSchemaAPI(Schema):
    name: str
    email: str
    age: int
    avatar_url: Optional[str] = None


@api.post("/users")
def create_user(request, data: UserSchemaAPI):
    return data


@api.patch("/users/{user_id}")
def update_user(request, user_id: int, data: PatchSchema[UserSchemaAPI]):
    # Return the data and its type to verify it's working correctly
    return {"id": user_id, "data": data.model_dump(), "type": str(type(data).__name__)}


def test_api_integration():
    # First create a user
    create_response = client.post(
        "/users", json={"name": "Test User", "email": "test@example.com", "age": 30}
    )
    assert create_response.status_code == 200

    # Test partial update with patch
    patch_response = client.patch("/users/1", json={"name": "Updated Name"})
    assert patch_response.status_code == 200
    assert patch_response.json() == {
        "id": 1,
        "data": {"name": "Updated Name"},
        "type": f"Patched{UserSchemaAPI.__name__}",
    }

    # Test multiple fields update
    patch_response = client.patch("/users/1", json={"name": "New Name", "age": 31})
    assert patch_response.status_code == 200
    assert patch_response.json() == {
        "id": 1,
        "data": {"name": "New Name", "age": 31},
        "type": f"Patched{UserSchemaAPI.__name__}",
    }

    # Test optional field set to null
    patch_response = client.patch("/users/1", json={"avatar_url": None})
    assert patch_response.status_code == 200
    assert patch_response.json() == {
        "id": 1,
        "data": {"avatar_url": None},
        "type": f"Patched{UserSchemaAPI.__name__}",
    }

    # Test validation error when setting non-optional field to null
    error_response = client.patch("/users/1", json={"name": None})
    assert error_response.status_code == 422  # Validation error


def test_direct_instantiation_error():
    with pytest.raises(TypeError) as exc_info:
        PatchSchema()

    assert "Cannot instantiate abstract PatchSchema class" in str(exc_info.value)


def test_subclass_error():
    with pytest.raises(TypeError) as exc_info:

        class MyPatchSchema(PatchSchema):
            pass

    assert "Cannot subclass" in str(exc_info.value)


def test_openapi_schema():
    """Test that the OpenAPI schema for a patched model is correctly generated."""
    schema = api.get_openapi_schema()
    patched_schema = schema["components"]["schemas"][f"Patched{UserSchemaAPI.__name__}"]

    assert patched_schema["type"] == "object"
    assert "properties" in patched_schema

    # Check that name is optional in the schema
    assert "name" in patched_schema["properties"]

    # In Pydantic v2, optional fields use anyOf with multiple types including null
    name_prop = patched_schema["properties"]["name"]
    assert "anyOf" in name_prop
    assert any(item["type"] == "string" for item in name_prop["anyOf"])
    assert any(item["type"] == "null" for item in name_prop["anyOf"])

    # No required fields in patched schema
    assert "required" not in patched_schema or "name" not in patched_schema["required"]

    # Check that avatar_url is still optional
    assert "avatar_url" in patched_schema["properties"]
    avatar_prop = patched_schema["properties"]["avatar_url"]
    assert "anyOf" in avatar_prop
    assert any(item["type"] == "string" for item in avatar_prop["anyOf"])
    assert any(item["type"] == "null" for item in avatar_prop["anyOf"])
