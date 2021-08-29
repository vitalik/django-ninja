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
                "title": "SchemaWithAlias",
                "type": "object",
                "properties": {
                    "foo": {"title": "Bar", "default": "", "type": "string"}
                },
            }
        }
    }


# TODO: check the conflicting approach
#       when alias is used both for response and request schema
#       basically it need to generate 2 schemas - one with alias another without
# @api.post("/path", response=SchemaWithAlias)
# def alias_operation(request, payload: SchemaWithAlias):
#     return {"bar": payload.foo}
