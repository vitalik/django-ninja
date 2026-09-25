from typing import List

import pytest

from ninja import NinjaAPI, Router, Schema
from ninja.testing import TestClient


class Pet(Schema):
    id: int
    name: str


class PetDeletedEvent(Schema):
    id: int
    reason: str


def test_webhook_with_body_renders_in_schema():
    api = NinjaAPI()

    @api.webhook("petCreated", response={200: None})
    def pet_created(request, payload: Pet):
        """Fired when a pet is added to the catalog."""

    schema = api.get_openapi_schema()

    assert "webhooks" in schema
    operation = schema["webhooks"]["petCreated"]["post"]
    assert operation["requestBody"]["content"]["application/json"]["schema"] == {
        "$ref": "#/components/schemas/Pet"
    }
    assert operation["responses"][200] == {"description": "OK"}
    assert operation["description"] == "Fired when a pet is added to the catalog."
    assert schema["components"]["schemas"]["Pet"] == {
        "title": "Pet",
        "type": "object",
        "properties": {
            "id": {"title": "Id", "type": "integer"},
            "name": {"title": "Name", "type": "string"},
        },
        "required": ["id", "name"],
    }


def test_webhook_only_api_has_empty_paths():
    api = NinjaAPI()

    @api.webhook("petDeleted")
    def pet_deleted(request, payload: PetDeletedEvent):
        pass

    schema = api.get_openapi_schema()

    assert schema["paths"] == {}
    assert list(schema["webhooks"].keys()) == ["petDeleted"]


def test_webhook_shares_components_with_paths():
    api = NinjaAPI()

    @api.get("/pets/{pet_id}", response=Pet)
    def get_pet(request, pet_id: int):
        return {"id": pet_id, "name": "Rex"}

    @api.webhook("petCreated")
    def pet_created(request, payload: Pet):
        pass

    schema = api.get_openapi_schema()

    get_op = schema["paths"]["/api/pets/{pet_id}"]["get"]
    webhook_op = schema["webhooks"]["petCreated"]["post"]

    assert get_op["responses"][200]["content"]["application/json"]["schema"] == {
        "$ref": "#/components/schemas/Pet"
    }
    assert webhook_op["requestBody"]["content"]["application/json"]["schema"] == {
        "$ref": "#/components/schemas/Pet"
    }
    assert list(schema["components"]["schemas"].keys()) == ["Pet"]


def test_webhook_on_subrouter_is_top_level():
    api = NinjaAPI()
    subrouter = Router()

    @subrouter.webhook("petCreated")
    def pet_created(request, payload: Pet):
        pass

    api.add_router("/v2", subrouter)

    schema = api.get_openapi_schema()

    # Webhook name is not prefixed with the mounted router's path
    assert "petCreated" in schema["webhooks"]
    assert "/v2/petCreated" not in schema["webhooks"]


def test_webhook_does_not_register_url_pattern():
    api = NinjaAPI()

    @api.webhook("petCreated")
    def pet_created(request, payload: Pet):
        pass

    url_patterns, _, _ = api.urls
    names = {getattr(p, "name", None) for p in url_patterns}
    assert "pet_created" not in names
    assert "petCreated" not in names

    client = TestClient(api)
    with pytest.raises(Exception, match='Cannot resolve "/petCreated"'):
        client.post("/petCreated", json={"id": 1, "name": "Rex"})


def test_empty_webhooks_preserves_schema_shape():
    api = NinjaAPI()

    @api.get("/ping")
    def ping(request):
        return "pong"

    schema = api.get_openapi_schema()

    assert "webhooks" not in schema


def test_webhook_response_models_documented():
    api = NinjaAPI()

    class Ack(Schema):
        received: bool

    @api.webhook("petCreated", response={202: Ack})
    def pet_created(request, payload: Pet):
        pass

    schema = api.get_openapi_schema()

    op = schema["webhooks"]["petCreated"]["post"]
    assert op["responses"][202]["content"]["application/json"]["schema"] == {
        "$ref": "#/components/schemas/Ack"
    }


def test_webhook_with_custom_methods():
    api = NinjaAPI()

    def pet_updated(request, payload: Pet):
        pass

    api.add_api_webhook("petUpdated", ["PUT"], pet_updated)

    schema = api.get_openapi_schema()

    assert list(schema["webhooks"]["petUpdated"].keys()) == ["put"]


def test_webhook_tags_and_operation_id():
    api = NinjaAPI()

    @api.webhook(
        "petCreated",
        tags=["pets", "events"],
        operation_id="pets.events.created",
        summary="Pet created event",
    )
    def pet_created(request, payload: Pet):
        pass

    op = api.get_openapi_schema()["webhooks"]["petCreated"]["post"]
    assert op["operationId"] == "pets.events.created"
    assert op["tags"] == ["pets", "events"]
    assert op["summary"] == "Pet created event"


def test_async_webhook_function_supported():
    api = NinjaAPI()

    @api.webhook("petCreated")
    async def pet_created(request, payload: Pet):
        pass

    op = api.get_openapi_schema()["webhooks"]["petCreated"]["post"]
    assert op["requestBody"]["content"]["application/json"]["schema"] == {
        "$ref": "#/components/schemas/Pet"
    }


def test_webhook_via_add_api_webhook():
    api = NinjaAPI()

    def pet_created(request, payload: Pet):
        pass

    api.add_api_webhook("petCreated", ["POST"], pet_created)

    schema = api.get_openapi_schema()
    assert "petCreated" in schema["webhooks"]


def test_webhook_with_list_payload():
    api = NinjaAPI()

    @api.webhook("petsBatchCreated")
    def pets_batch_created(request, payload: List[Pet]):
        pass

    op = api.get_openapi_schema()["webhooks"]["petsBatchCreated"]["post"]
    schema = op["requestBody"]["content"]["application/json"]["schema"]
    assert schema == {
        "type": "array",
        "items": {"$ref": "#/components/schemas/Pet"},
        "title": "Payload",
    }
