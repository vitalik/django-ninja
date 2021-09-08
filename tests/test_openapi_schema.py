import pytest
from typing import List
from django.test import Client, override_settings

from ninja import Body, Form, NinjaAPI, Schema, UploadedFile
from ninja.errors import ConfigError

api = NinjaAPI()


class Payload(Schema):
    i: int
    f: float


def to_camel(string: str) -> str:
    return "".join(word.capitalize() for word in string.split("_"))


class Response(Schema):
    i: int
    f: float

    class Config(Schema.Config):
        alias_generator = to_camel
        allow_population_by_field_name = True


@api.post("/test", response=Response)
def method(request, data: Payload):
    return data.dict()


@api.post("/test-alias", response=Response, by_alias=True)
def method_alias(request, data: Payload):
    return data.dict()


@api.post("/test_list", response=List[Response])
def method_list_response(request, data: List[Payload]):
    return []


@api.post("/test-body", response=Response)
def method_body(request, i: int = Body(...), f: float = Body(...)):
    return dict(i=i, f=f)


@api.post("/test-body-schema", response=Response)
def method_body_schema(request, data: Payload):
    return dict(i=data.i, f=data.f)


@api.get("/test-path/{int:i}/{f}", response=Response)
def method_path(request, i: int, f: float):
    return dict(i=i, f=f)


@api.post("/test-form", response=Response)
def method_form(request, data: Payload = Form(...)):
    return dict(i=data.i, f=data.f)


@api.post("/test-form-file", response=Response)
def method_form_file(request, files: List[UploadedFile], data: Payload = Form(...)):
    return dict(i=data.i, f=data.f)


def test_schema_views(client: Client):
    assert client.get("/api/").status_code == 404
    assert client.get("/api/docs").status_code == 200
    assert client.get("/api/openapi.json").status_code == 200


def test_schema_views_no_INSTALLED_APPS(client: Client):
    "Making sure that cdn and included js works fine"
    from django.conf import settings

    # removing ninja from settings:
    INSTALLED_APPS = [i for i in settings.INSTALLED_APPS if i != "ninja"]

    @override_settings(INSTALLED_APPS=INSTALLED_APPS)
    def call_docs():
        assert client.get("/api/docs").status_code == 200

    call_docs()


@pytest.fixture(scope="session")
def schema():
    return api.get_openapi_schema()


def test_schema(schema):
    method = schema["paths"]["/api/test"]["post"]

    assert method["requestBody"] == {
        "content": {
            "application/json": {"schema": {"$ref": "#/components/schemas/Payload"}}
        },
        "required": True,
    }
    assert method["responses"] == {
        200: {
            "content": {
                "application/json": {
                    "schema": {"$ref": "#/components/schemas/Response"}
                }
            },
            "description": "OK",
        }
    }
    assert schema.schemas == {
        "Response": {
            "title": "Response",
            "type": "object",
            "properties": {
                "i": {"title": "I", "type": "integer"},
                "f": {"title": "F", "type": "number"},
            },
            "required": ["i", "f"],
        },
        "Payload": {
            "title": "Payload",
            "type": "object",
            "properties": {
                "i": {"title": "I", "type": "integer"},
                "f": {"title": "F", "type": "number"},
            },
            "required": ["i", "f"],
        },
    }


def test_schema_alias(schema):
    method = schema["paths"]["/api/test-alias"]["post"]

    assert method["requestBody"] == {
        "content": {
            "application/json": {"schema": {"$ref": "#/components/schemas/Payload"}}
        },
        "required": True,
    }
    assert method["responses"] == {
        200: {
            "content": {
                "application/json": {
                    "schema": {"$ref": "#/components/schemas/Response"}
                }
            },
            "description": "OK",
        }
    }
    # ::TODO:: this is currently broken if not all responses for same schema use the same by_alias
    '''
    assert schema.schemas == {
        "Response": {
            "title": "Response",
            "type": "object",
            "properties": {
                "I": {"title": "I", "type": "integer"},
                "F": {"title": "F", "type": "number"},
            },
            "required": ["i", "f"],
        },
        "Payload": {
            "title": "Payload",
            "type": "object",
            "properties": {
                "i": {"title": "I", "type": "integer"},
                "f": {"title": "F", "type": "number"},
            },
            "required": ["i", "f"],
        },
    }
    '''


def test_schema_list(schema):
    method_list = schema["paths"]["/api/test_list"]["post"]

    assert method_list["requestBody"] == {
        "content": {
            "application/json": {
                "schema": {
                    "items": {"$ref": "#/components/schemas/Payload"},
                    "title": "Data",
                    "type": "array",
                }
            }
        },
        "required": True,
    }
    assert method_list["responses"] == {
        200: {
            "content": {
                "application/json": {
                    "schema": {
                        "items": {"$ref": "#/components/schemas/Response"},
                        "title": "Response",
                        "type": "array",
                    }
                }
            },
            "description": "OK",
        }
    }

    assert schema["components"]["schemas"] == {
        "Payload": {
            "properties": {
                "f": {"title": "F", "type": "number"},
                "i": {"title": "I", "type": "integer"},
            },
            "required": ["i", "f"],
            "title": "Payload",
            "type": "object",
        },
        "Response": {
            "properties": {
                "f": {"title": "F", "type": "number"},
                "i": {"title": "I", "type": "integer"},
            },
            "required": ["i", "f"],
            "title": "Response",
            "type": "object",
        },
    }


def test_schema_body(schema):
    method_list = schema["paths"]["/api/test-body"]["post"]

    assert method_list["requestBody"] == {
        "content": {
            "application/json": {
                "schema": {
                    "properties": {
                        "f": {"title": "F", "type": "number"},
                        "i": {"title": "I", "type": "integer"},
                    },
                    "required": ["i", "f"],
                    "title": "BodyParams",
                    "type": "object",
                }
            }
        },
        "required": True,
    }
    assert method_list["responses"] == {
        200: {
            "content": {
                "application/json": {
                    "schema": {"$ref": "#/components/schemas/Response"}
                }
            },
            "description": "OK",
        }
    }


def test_schema_body_schema(schema):
    method_list = schema["paths"]["/api/test-body-schema"]["post"]

    assert method_list["requestBody"] == {
        "content": {
            "application/json": {"schema": {"$ref": "#/components/schemas/Payload"}},
        },
        "required": True,
    }
    assert method_list["responses"] == {
        200: {
            "content": {
                "application/json": {
                    "schema": {"$ref": "#/components/schemas/Response"}
                }
            },
            "description": "OK",
        }
    }


def test_schema_path(schema):
    method_list = schema["paths"]["/api/test-path/{i}/{f}"]["get"]

    assert "requestBody" not in method_list

    assert method_list["parameters"] == [
        {
            "in": "path",
            "name": "i",
            "schema": {"title": "I", "type": "integer"},
            "required": True,
        },
        {
            "in": "path",
            "name": "f",
            "schema": {"title": "F", "type": "number"},
            "required": True,
        },
    ]

    assert method_list["responses"] == {
        200: {
            "content": {
                "application/json": {
                    "schema": {"$ref": "#/components/schemas/Response"},
                },
            },
            "description": "OK",
        }
    }


def test_schema_form(schema):
    method_list = schema["paths"]["/api/test-form"]["post"]

    assert method_list["requestBody"] == {
        "content": {
            "application/x-www-form-urlencoded": {
                "schema": {"$ref": "#/components/schemas/Payload"}
            }
        },
        "required": True,
    }
    assert method_list["responses"] == {
        200: {
            "description": "OK",
            "content": {
                "application/json": {
                    "schema": {"$ref": "#/components/schemas/Response"}
                }
            },
        }
    }


def test_schema_form_file(schema):
    method_list = schema["paths"]["/api/test-form-file"]["post"]

    assert method_list["requestBody"] == {
        "content": {
            "multipart/form-data": {
                "schema": {
                    "properties": {
                        "data": {"$ref": "#/components/schemas/Payload"},
                        "files": {
                            "items": {"format": "binary", "type": "string"},
                            "title": "Files",
                            "type": "array",
                        },
                    },
                    "required": ["files", "data"],
                    "title": "FormFileParams",
                    "type": "object",
                }
            }
        },
        "required": True,
    }
    assert method_list["responses"] == {
        200: {
            "description": "OK",
            "content": {
                "application/json": {
                    "schema": {"$ref": "#/components/schemas/Response"}
                }
            },
        }
    }


def test_unique_operation_ids():

    api = NinjaAPI()

    @api.get("/1")
    def same_name(request):
        pass

    @api.get("/2")
    def same_name(request):
        pass

    with pytest.warns(UserWarning):
        api.get_openapi_schema()


def test_body_file():
    api = NinjaAPI()

    @api.post("/test")
    def method(request, data: Payload, files: UploadedFile):
        pass

    match = "'Body' params currently incompatible with 'File' params"
    with pytest.raises(ConfigError, match=match):
        api.get_openapi_schema()
