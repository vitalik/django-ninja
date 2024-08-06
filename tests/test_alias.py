from pydantic import ConfigDict
from pydantic.alias_generators import to_camel

from ninja import Field, NinjaAPI, Schema
from ninja.testing import TestClient


class SchemaWithAlias(Schema):
    foo: str = Field("", alias="bar")


api = NinjaAPI()


@api.get("/path", response=SchemaWithAlias)
def alias_operation(request):
    return {"bar": "value"}


def test_alias():
    schema = api.get_openapi_schema()["components"]
    print(schema)
    assert schema == {
        "schemas": {
            "SchemaWithAlias": {
                "type": "object",
                "properties": {
                    "foo": {"type": "string", "default": "", "title": "Foo"}
                },
                "title": "SchemaWithAlias",
            }
        }
    }


# Make sure that both "runtime" (request/response) AND the generated openapi schemas respect the alias generator when controlling it with the "by_alias" parameter
# Before, the request body was not respected when generating the openapi schema.


class SchemaBodyWithAliasGenerator(Schema):
    model_config = ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True,
    )
    foo_bar: str = Field("")


class SchemaResponseWithAliasGenerator(Schema):
    model_config = ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True,
    )
    foo_bar: str = Field("")


api_without_alias = NinjaAPI()


@api_without_alias.post(
    "/path-without-alias", response=SchemaResponseWithAliasGenerator, by_alias=False
)
def alias_operation_without_alias(request, payload: SchemaBodyWithAliasGenerator):
    return {"foo_bar": payload.foo_bar}


def test_response_and_body_without_alias():
    client = TestClient(api_without_alias)
    assert client.post(
        "/path-without-alias", json={"foo_bar": "foo_bar indeed"}
    ).json() == {"foo_bar": "foo_bar indeed"}

    schema = api_without_alias.get_openapi_schema()["components"]
    print(schema)

    assert schema == {
        "schemas": {
            "SchemaBodyWithAliasGenerator": {
                "type": "object",
                "properties": {
                    "foo_bar": {"type": "string", "default": "", "title": "Foo Bar"}
                },
                "title": "SchemaBodyWithAliasGenerator",
            },
            "SchemaResponseWithAliasGenerator": {
                "type": "object",
                "properties": {
                    "foo_bar": {"type": "string", "default": "", "title": "Foo Bar"}
                },
                "title": "SchemaResponseWithAliasGenerator",
            },
        }
    }


api_with_alias = NinjaAPI()


@api_with_alias.post(
    "/path-with-alias", response=SchemaResponseWithAliasGenerator, by_alias=True
)
def alias_operation_with_alias(request, payload: SchemaBodyWithAliasGenerator):
    return {"foo_bar": payload.foo_bar}


def test_response_and_body_with_alias():
    client = TestClient(api_with_alias)
    assert client.post("/path-with-alias", json={"fooBar": "fooBar indeed"}).json() == {
        "fooBar": "fooBar indeed"
    }

    schema = api_with_alias.get_openapi_schema()["components"]
    print(schema)

    assert schema == {
        "schemas": {
            "SchemaBodyWithAliasGenerator": {
                "type": "object",
                "properties": {
                    "fooBar": {"type": "string", "default": "", "title": "Foobar"}
                },
                "title": "SchemaBodyWithAliasGenerator",
            },
            "SchemaResponseWithAliasGenerator": {
                "type": "object",
                "properties": {
                    "fooBar": {"type": "string", "default": "", "title": "Foobar"}
                },
                "title": "SchemaResponseWithAliasGenerator",
            },
        }
    }


# TODO: check the conflicting approach
#       when alias is used both for response and request schema
#       basically it need to generate 2 schemas - one with alias another without
# @api.post("/path", response=SchemaWithAlias)
# def alias_operation(request, payload: SchemaWithAlias):
#     return {"bar": payload.foo}
