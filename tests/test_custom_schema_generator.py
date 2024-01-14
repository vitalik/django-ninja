import pytest
from pydantic.json_schema import CoreModeRef, DefsRef

from ninja import NinjaAPI
from ninja.conf import settings
from ninja.schema import Field, NinjaGenerateJsonSchema, Schema


class FullSchemaNameGenerator(NinjaGenerateJsonSchema):
    def get_defs_ref(self, core_mode_ref: CoreModeRef) -> DefsRef:
        temp = super().get_defs_ref(core_mode_ref)
        choices = self._prioritized_defsref_choices[temp]
        choices.pop(0)
        choices.pop(0)
        self._prioritized_defsref_choices[temp] = choices
        return temp


class Payload(Schema):
    i: int
    f: float


def to_camel(string: str) -> str:
    return "".join(word.capitalize() for word in string.split("_"))


class Response(Schema):
    i: int
    f: float = Field(..., title="f title", description="f desc")

    class Config(Schema.Config):
        alias_generator = to_camel
        populate_by_name = True


@pytest.fixture(scope="function")
def schema():
    # setup up
    settings.SCHEMA_GENERATOR_CLASS = (
        "tests.test_custom_schema_generator.FullSchemaNameGenerator"
    )
    api = NinjaAPI()

    @api.post("/test", response=Response)
    def method(request, data: Payload):
        return data.dict()

    yield api.get_openapi_schema()
    # reset
    settings.SCHEMA_GENERATOR_CLASS = "ninja.schema.NinjaGenerateJsonSchema"


def test_full_name_schema(schema):
    method = schema["paths"]["/api/test"]["post"]

    assert method["requestBody"] == {
        "content": {
            "application/json": {
                "schema": {
                    "$ref": "#/components/schemas/test_custom_schema_generator__Payload"
                }
            }
        },
        "required": True,
    }
    assert method["responses"] == {
        200: {
            "content": {
                "application/json": {
                    "schema": {
                        "$ref": "#/components/schemas/test_custom_schema_generator__Response"
                    }
                }
            },
            "description": "OK",
        }
    }
    assert schema.schemas == {
        "test_custom_schema_generator__Response": {
            "title": "Response",
            "type": "object",
            "properties": {
                "i": {"title": "I", "type": "integer"},
                "f": {"description": "f desc", "title": "f title", "type": "number"},
            },
            "required": ["i", "f"],
        },
        "test_custom_schema_generator__Payload": {
            "title": "Payload",
            "type": "object",
            "properties": {
                "i": {"title": "I", "type": "integer"},
                "f": {"title": "F", "type": "number"},
            },
            "required": ["i", "f"],
        },
    }
