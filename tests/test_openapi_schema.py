from typing import List, Union
from unittest.mock import Mock

import pytest
from django.contrib.admin.views.decorators import staff_member_required
from django.test import Client, override_settings

from ninja import Body, Field, File, Form, NinjaAPI, Query, Schema, UploadedFile
from ninja.openapi.urls import get_openapi_urls

api = NinjaAPI()


class Payload(Schema):
    i: int
    f: float


class TypeA(Schema):
    a: str


class TypeB(Schema):
    b: str


def to_camel(string: str) -> str:
    return "".join(word.capitalize() for word in string.split("_"))


class Response(Schema):
    i: int
    f: float = Field(..., title="f title", description="f desc")

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


@api.post("/test-form-single", response=Response)
def method_form_single(request, data: float = Form(...)):
    return dict(i=int(data), f=data)


@api.post("/test-form-body", response=Response)
def method_form_body(request, i: int = Form(10), s: str = Body("10")):
    return dict(i=i, s=s)


@api.post("/test-form-file", response=Response)
def method_form_file(request, files: List[UploadedFile], data: Payload = Form(...)):
    return dict(i=data.i, f=data.f)


@api.post("/test-body-file", response=Response)
def method_body_file(
    request,
    files: List[UploadedFile],
    body: Payload = Body(...),
):
    return dict(i=body.i, f=body.f)


@api.post("/test-union-type", response=Response)
def method_union_payload(request, data: Union[TypeA, TypeB]):
    return dict(i=data.i, f=data.f)


@api.post("/test-union-type-with-simple", response=Response)
def method_union_payload_and_simple(request, data: Union[int, TypeB]):
    return data.dict()


@api.post(
    "/test-title-description/",
    tags=["a-tag"],
    summary="Best API Ever",
    response=Response,
)
def method_test_title_description(
    request,
    param1: int = Query(..., title="param 1 title"),
    param2: str = Query("A Default", description="param 2 desc"),
    file: UploadedFile = File(..., description="file param desc"),
):
    return dict(i=param1, f=param2)


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
                "f": {"description": "f desc", "title": "f title", "type": "number"},
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
        "TypeA": {
            "properties": {
                "a": {"title": "A", "type": "string"},
            },
            "required": ["a"],
            "title": "TypeA",
            "type": "object",
        },
        "TypeB": {
            "properties": {
                "b": {"title": "B", "type": "string"},
            },
            "required": ["b"],
            "title": "TypeB",
            "type": "object",
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
    """
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
    """


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
        "TypeA": {
            "properties": {
                "a": {"title": "A", "type": "string"},
            },
            "required": ["a"],
            "title": "TypeA",
            "type": "object",
        },
        "TypeB": {
            "properties": {
                "b": {"title": "B", "type": "string"},
            },
            "required": ["b"],
            "title": "TypeB",
            "type": "object",
        },
        "Response": {
            "properties": {
                "f": {"description": "f desc", "title": "f title", "type": "number"},
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
                "schema": {
                    "properties": {
                        "f": {"title": "F", "type": "number"},
                        "i": {"title": "I", "type": "integer"},
                    },
                    "required": ["i", "f"],
                    "title": "FormParams",
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


def test_schema_single(schema):
    method_list = schema["paths"]["/api/test-form-single"]["post"]

    assert method_list["requestBody"] == {
        "content": {
            "application/x-www-form-urlencoded": {
                "schema": {
                    "properties": {"data": {"title": "Data", "type": "number"}},
                    "required": ["data"],
                    "title": "FormParams",
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


def test_schema_form_body(schema):
    method_list = schema["paths"]["/api/test-form-body"]["post"]

    assert method_list["requestBody"] == {
        "content": {
            "multipart/form-data": {
                "schema": {
                    "properties": {
                        "i": {"default": 10, "title": "I", "type": "integer"},
                        "s": {"default": "10", "title": "S", "type": "string"},
                    },
                    "title": "MultiPartBodyParams",
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


def test_schema_form_file(schema):
    method_list = schema["paths"]["/api/test-form-file"]["post"]

    assert method_list["requestBody"] == {
        "content": {
            "multipart/form-data": {
                "schema": {
                    "properties": {
                        "f": {"title": "F", "type": "number"},
                        "files": {
                            "items": {"format": "binary", "type": "string"},
                            "title": "Files",
                            "type": "array",
                        },
                        "i": {"title": "I", "type": "integer"},
                    },
                    "required": ["files", "i", "f"],
                    "title": "MultiPartBodyParams",
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


def test_schema_body_file(schema):
    method_list = schema["paths"]["/api/test-body-file"]["post"]

    assert method_list["requestBody"] == {
        "content": {
            "multipart/form-data": {
                "schema": {
                    "properties": {
                        "body": {"$ref": "#/components/schemas/Payload"},
                        "files": {
                            "items": {"format": "binary", "type": "string"},
                            "title": "Files",
                            "type": "array",
                        },
                    },
                    "required": ["files", "body"],
                    "title": "MultiPartBodyParams",
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


def test_schema_title_description(schema):
    method_list = schema["paths"]["/api/test-title-description/"]["post"]

    assert method_list["summary"] == "Best API Ever"
    assert method_list["tags"] == ["a-tag"]

    assert method_list["requestBody"] == {
        "content": {
            "multipart/form-data": {
                "schema": {
                    "properties": {
                        "file": {
                            "description": "file " "param " "desc",
                            "format": "binary",
                            "title": "File",
                            "type": "string",
                        }
                    },
                    "required": ["file"],
                    "title": "FileParams",
                    "type": "object",
                }
            }
        },
        "required": True,
    }

    assert method_list["parameters"] == [
        {
            "in": "query",
            "name": "param1",
            "required": True,
            "schema": {"title": "param 1 title", "type": "integer"},
        },
        {
            "in": "query",
            "name": "param2",
            "description": "param 2 desc",
            "required": False,
            "schema": {
                "default": "A Default",
                "description": "param 2 desc",
                "title": "Param2",
                "type": "string",
            },
        },
    ]

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


def test_union_payload_type(schema):
    method = schema["paths"]["/api/test-union-type"]["post"]

    assert method["requestBody"] == {
        "content": {
            "application/json": {
                "schema": {
                    "anyOf": [
                        {"$ref": "#/components/schemas/TypeA"},
                        {"$ref": "#/components/schemas/TypeB"},
                    ],
                    "title": "Data",
                }
            }
        },
        "required": True,
    }


def test_union_payload_simple(schema):
    method = schema["paths"]["/api/test-union-type-with-simple"]["post"]

    print(method["requestBody"])
    assert method["requestBody"] == {
        "content": {
            "application/json": {
                "schema": {
                    "title": "Data",
                    "anyOf": [
                        {"type": "integer"},
                        {"$ref": "#/components/schemas/TypeB"},
                    ],
                }
            }
        },
        "required": True,
    }


def test_get_openapi_urls():

    api = NinjaAPI(openapi_url=None)
    paths = get_openapi_urls(api)
    assert len(paths) == 0

    api = NinjaAPI(docs_url=None)
    paths = get_openapi_urls(api)
    assert len(paths) == 1

    api = NinjaAPI(openapi_url="/path", docs_url="/path")
    with pytest.raises(
        AssertionError, match="Please use different urls for openapi_url and docs_url"
    ):
        get_openapi_urls(api)


def test_unique_operation_ids():

    api = NinjaAPI()

    @api.get("/1")
    def same_name(request):
        pass

    @api.get("/2")  # noqa: F811
    def same_name(request):  # noqa: F811
        pass

    match = 'operation_id "test_openapi_schema_same_name" is already used'
    with pytest.warns(UserWarning, match=match):
        api.get_openapi_schema()


def test_docs_decorator():
    api = NinjaAPI(docs_decorator=staff_member_required)

    paths = get_openapi_urls(api)
    assert len(paths) == 2
    for ptrn in paths:
        request = Mock(user=Mock(is_staff=True))
        result = ptrn.callback(request)
        assert result.status_code == 200

        request = Mock(user=Mock(is_staff=False))
        request.build_absolute_uri = lambda: "http://example.com"
        result = ptrn.callback(request)
        assert result.status_code == 302
