"""ModelSchema / create_schema support for ForeignKey attnames (`user_id`).

Django exposes a ForeignKey's raw value under its attname (`user_id`
for a `user` FK). Listing that attname in `fields`, `exclude` or
`fields_optional` used to raise ConfigError ("are not in model")
even though it is the natural way to ask for the raw key.
"""

import pytest
from django.db import models

from ninja import NinjaAPI
from ninja.errors import ConfigError
from ninja.orm import ModelSchema, create_schema
from ninja.testing import TestClient


class AttUser(models.Model):
    name = models.CharField(max_length=50)

    class Meta:
        app_label = "tests"


class AttOrder(models.Model):
    title = models.CharField(max_length=50)
    user = models.ForeignKey(AttUser, on_delete=models.CASCADE)

    class Meta:
        app_label = "tests"


def test_create_schema_fields_by_attname():
    Schema = create_schema(AttOrder, fields=["id", "user_id"])
    assert set(Schema.model_fields) == {"id", "user_id"}

    order = AttOrder(id=1, title="x", user_id=42)
    data = Schema.from_orm(order).dict()
    assert data == {"id": 1, "user_id": 42}

    payload = Schema(**{"id": 2, "user_id": 7})
    assert payload.user_id == 7


def test_create_schema_attname_is_typed_as_related_pk():
    Schema = create_schema(AttOrder, fields=["user_id"])
    annotation = Schema.model_fields["user_id"].annotation
    # the raw key is an int (the related model's pk type), not a schema
    assert annotation is int


def test_create_schema_exclude_by_attname():
    Schema = create_schema(AttOrder, exclude=["user_id"])
    assert "user" not in Schema.model_fields
    assert "user_id" not in Schema.model_fields
    assert "title" in Schema.model_fields


def test_create_schema_exclude_by_name_still_works():
    Schema = create_schema(AttOrder, exclude=["user"])
    assert "user" not in Schema.model_fields
    assert "title" in Schema.model_fields


def test_fields_by_name_unchanged():
    Schema = create_schema(AttOrder, fields=["id", "user"])
    assert set(Schema.model_fields) == {"id", "user"}
    order = AttOrder(id=1, title="x", user_id=42)
    assert Schema.from_orm(order).dict() == {"id": 1, "user": 42}
    assert Schema.from_orm(order).dict(by_alias=True) == {"id": 1, "user_id": 42}


def test_attname_optional():
    Schema = create_schema(
        AttOrder, fields=["id", "user_id"], optional_fields=["user_id"]
    )
    payload = Schema(**{"id": 1})
    assert payload.user_id is None


def test_invalid_field_still_rejected():
    with pytest.raises(ConfigError):
        create_schema(AttOrder, fields=["user_uuid"])


def test_modelschema_meta_fields_by_attname():
    class OrderOut(ModelSchema):
        class Meta:
            model = AttOrder
            fields = ["id", "user_id"]

    order = AttOrder(id=3, title="t", user_id=9)
    assert OrderOut.from_orm(order).dict() == {"id": 3, "user_id": 9}


def test_attname_field_roundtrip_through_api():
    Schema = create_schema(AttOrder, fields=["id", "title", "user_id"])

    api = NinjaAPI()

    @api.post("/orders")
    def create_order(request, payload: Schema):
        return payload.dict()

    client = TestClient(api)
    response = client.post("/orders", json={"id": 1, "title": "a", "user_id": 5})
    assert response.status_code == 200, str(response.json())
    assert response.json() == {"id": 1, "title": "a", "user_id": 5}

    spec = client.get("/openapi.json").json()
    schemas = spec["components"]["schemas"]
    order_schemas = [s for s in schemas.values() if "user_id" in s.get("properties", {})]
    assert len(order_schemas) == 1
    assert order_schemas[0]["properties"]["user_id"]["type"] == "integer"
