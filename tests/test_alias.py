from types import SimpleNamespace
from typing import Optional

from ninja import Field, NinjaAPI, Schema


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


# TODO: check the conflicting approach
#       when alias is used both for response and request schema
#       basically it need to generate 2 schemas - one with alias another without
# @api.post("/path", response=SchemaWithAlias)
# def alias_operation(request, payload: SchemaWithAlias):
#     return {"bar": payload.foo}


class NumericAliasShift(Schema):
    start: Optional[str] = None


class NumericAliasDay(Schema):
    # JSON keys are always strings, but "0" is not a valid python identifier,
    # so an alias is the only way to declare a field with that key.
    first: Optional[NumericAliasShift] = Field(None, alias="0")

    model_config = {"populate_by_name": True}


def test_numeric_alias_from_object():
    """
    Object input goes through DjangoGetter, which falls back to django's template
    Variable when an attribute is missing. Variable("0") is the number 0 and not
    a lookup, so the alias must not resolve to it. (Dict input never gets there.)
    """
    day = SimpleNamespace(first=SimpleNamespace(start="09:00"))
    result = NumericAliasDay.model_validate(day)
    assert result.model_dump(by_alias=True) == {"0": {"start": "09:00"}}

    # also when the input is a schema instance, as in a response
    result = NumericAliasDay.model_validate(result)
    assert result.model_dump(by_alias=True) == {"0": {"start": "09:00"}}

    # a missing attribute uses the default, instead of validating 0 as the schema
    assert NumericAliasDay.model_validate(SimpleNamespace()).first is None
