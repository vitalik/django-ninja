from ninja import Field, NinjaAPI, Schema


class SchemaWithAlias(Schema):
    foo: str = Field("", alias="bar")


api = NinjaAPI()


@api.get("/path", response=SchemaWithAlias)
def alias_operation(request):
    return {"bar": "value"}


def test_alias():
    schema = api.get_openapi_schema()["components"]
    assert schema['schemas']['SchemaWithAlias'] == {
        "type": "object",
        "properties": {
            "foo": {"type": "string", "default": "", "title": "Foo"}
        },
        "title": "SchemaWithAlias",
    }

    assert schema['schemas']['DefaultValidationError'] == {
        'properties': {
            'detail': {
                'items': {'$ref': '#/components/schemas/ValidationError'},
                'title': 'Detail', 'type': 'array'
            }
        },
        'required': ['detail'],
        'title': 'DefaultValidationError', 'type': 'object'
    }
    assert schema['schemas']['ValidationError'] == {
        'properties': {
            'loc': {
                'items': {
                    'anyOf': [{'type': 'string'}, {'type': 'integer'}]
                }, 'title': 'Loc', 'type': 'array'
            },
            'msg': {'title': 'Msg', 'type': 'string'},
            'type': {'title': 'Type', 'type': 'string'}
        },
        'required': ['loc', 'msg', 'type'], 'title': 'ValidationError', 'type': 'object'
    }

# TODO: check the conflicting approach
#       when alias is used both for response and request schema
#       basically it need to generate 2 schemas - one with alias another without
# @api.post("/path", response=SchemaWithAlias)
# def alias_operation(request, payload: SchemaWithAlias):
#     return {"bar": payload.foo}
