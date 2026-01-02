"""Test that request body schemas with forward references work correctly.

This test verifies the fix for the PydanticUserError issue where using
request body schemas would fail with 'BodyParams is not fully defined'.
"""
from typing import Any, Dict, Optional

import pytest
from ninja import NinjaAPI, Schema
from ninja.testing import TestClient


class RequestSchema(Schema):
    """Simple request schema with various field types."""

    name: Optional[str] = None
    content: Dict[str, Any]


class ResponseSchema(Schema):
    """Simple response schema."""

    success: bool
    data: Dict[str, Any]


api = NinjaAPI()


@api.post("/test", response=ResponseSchema)
def create_item(request, payload: RequestSchema):
    """Endpoint that accepts a request body schema."""
    return {
        "success": True,
        "data": {"name": payload.name, "content": payload.content},
    }


client = TestClient(api)


def test_post_with_body_schema():
    """Test POST endpoint with request body schema validates correctly."""
    response = client.post(
        "/test",
        json={
            "name": "test",
            "content": {"key": "value"},
        },
    )

    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    assert data["data"]["name"] == "test"
    assert data["data"]["content"] == {"key": "value"}


def test_post_with_body_schema_optional_field():
    """Test POST endpoint with optional field omitted."""
    response = client.post(
        "/test",
        json={
            "content": {"key": "value"},
        },
    )

    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    assert data["data"]["name"] is None
    assert data["data"]["content"] == {"key": "value"}


def test_post_with_invalid_body():
    """Test POST endpoint with invalid body returns 422."""
    response = client.post(
        "/test",
        json={
            "name": "test",
            # Missing required 'content' field
        },
    )

    assert response.status_code == 422
