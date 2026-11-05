from dataclasses import dataclass
from datetime import date
from decimal import Decimal
from enum import Enum
from typing import Any, Dict, List, Literal, Optional, Union

import pytest
from django.core.files.uploadedfile import SimpleUploadedFile
from pydantic import Field, HttpUrl, Json, RootModel
from pydantic_core import core_schema, to_jsonable_python
from typing_extensions import Annotated, TypedDict

from ninja import Body, File, Form, NinjaAPI, Schema, UploadedFile
from ninja.testing import TestClient

api = NinjaAPI()


@api.post("/str_and_file")
def str_and_file(
    request,
    title: str = Form(...),
    description: str = Form(""),
    file: UploadedFile = File(...),
):
    return {"title": title, "data": file.read().decode()}


@api.post("/str_body_and_file")
def str_body_and_file(
    request,
    title: str = Body(...),
    file: UploadedFile = File(...),
):
    return {"title": title, "data": file.read().decode()}


client = TestClient(api)


def test_files():
    file = SimpleUploadedFile("test.txt", b"data123")
    response = client.post(
        "/str_and_file",
        FILES={"file": file},
        POST={"title": "hello"},
    )
    assert response.status_code == 200
    assert response.json() == {"title": "hello", "data": "data123"}

    schema = api.get_openapi_schema()["paths"]["/api/str_and_file"]
    r_body = schema["post"]["requestBody"]

    assert r_body == {
        "content": {
            "multipart/form-data": {
                "schema": {
                    "title": "MultiPartBodyParams",
                    "type": "object",
                    "properties": {
                        "title": {"title": "Title", "type": "string"},
                        "description": {
                            "title": "Description",
                            "default": "",
                            "type": "string",
                        },
                        "file": {
                            "title": "File",
                            "type": "string",
                            "format": "binary",
                        },
                    },
                    "required": ["title", "file"],
                }
            }
        },
        "required": True,
    }


def test_empty_multipart_body_field():
    file = SimpleUploadedFile("test.txt", b"data123")
    response = client.post(
        "/str_body_and_file",
        FILES={"file": file},
        POST={"title": ""},
    )
    assert response.status_code == 200
    assert response.json() == {"title": "", "data": "data123"}


@pytest.mark.parametrize(
    "value", ["hello", 'say "hi"', "5'10\"", '"quoted"', "line1\nline2", "a\\nb"]
)
def test_multipart_str_body_passed_unchanged(value):
    file = SimpleUploadedFile("test.txt", b"data123")
    response = client.post(
        "/str_body_and_file", FILES={"file": file}, POST={"title": value}
    )
    assert response.status_code == 200, response.content
    assert response.json() == {"title": value, "data": "data123"}


def test_multipart_scalar_body_types():
    api = NinjaAPI()

    class Color(str, Enum):
        red = "red"

    @api.post("/scalars")
    def scalars(
        request,
        file: UploadedFile = File(...),
        n: int = Body(...),
        day: date = Body(...),
        color: Color = Body(...),
        note: Optional[str] = Body(None),
    ):
        return {"n": n, "day": str(day), "color": color, "note": note}

    file = SimpleUploadedFile("test.txt", b"data123")
    data = {"n": "42", "day": "2024-01-02", "color": "red", "note": "hello"}
    response = TestClient(api).post("/scalars", FILES={"file": file}, POST=data)
    assert response.status_code == 200, response.content
    assert response.json() == {**data, "n": 42}


def test_multipart_json_body_parts():
    api = NinjaAPI()

    class Details(Schema):
        title: str

    @api.post("/json-parts")
    def json_parts(
        request,
        details: Details,
        tags: List[str] = Body(...),
        meta: Dict[str, int] = Body(...),
        file: UploadedFile = File(...),
    ):
        return {"title": details.title, "tags": tags, "meta": meta}

    file = SimpleUploadedFile("test.txt", b"data123")
    response = TestClient(api).post(
        "/json-parts",
        FILES={"file": file},
        POST={
            "details": '{"title": "say \\"hi\\""}',
            "tags": '["a", "b"]',
            "meta": '{"x": 1}',
        },
    )
    assert response.status_code == 200, response.content
    assert response.json() == {
        "title": 'say "hi"',
        "tags": ["a", "b"],
        "meta": {"x": 1},
    }


class _Item(Schema):
    name: str = "default"


class _Point(TypedDict):
    x: int


@dataclass
class _DataPoint:
    x: int


class _Color(str, Enum):
    red = "red"


class _Name(RootModel[str]):
    pass


class _Opaque:
    """A custom type without a JSON schema."""

    @classmethod
    def __get_pydantic_core_schema__(cls, source, handler):
        return core_schema.no_info_plain_validator_function(lambda v: v)


@pytest.mark.parametrize(
    "annotation,value,expected",
    [
        # read as JSON
        (dict, '{"a": 1}', {"a": 1}),
        (Optional[Dict[str, int]], '{"a": 1}', {"a": 1}),
        (_Point, '{"x": 1}', {"x": 1}),
        (_DataPoint, '{"x": 1}', {"x": 1}),
        (Annotated[List[int], Field(min_length=1)], "[1, 2]", [1, 2]),
        (Any, '{"a": 1}', {"a": 1}),
        (Optional[_Item], '{"name": "sent"}', {"name": "sent"}),
        (Union[Literal["none"], _Item], '{"name": "sent"}', {"name": "sent"}),
        (_Opaque, '{"a": 1}', {"a": 1}),
        # a union with a structured branch is JSON as a whole
        (Union[str, Dict[str, int]], '{"a": 1}', {"a": 1}),
        (Union[str, Dict[str, int]], '"hello"', "hello"),
        # read as plain text
        (Optional[_Color], "red", "red"),
        (Literal[1, "a"], "a", "a"),
        (Decimal, "1.50", "1.50"),
        (HttpUrl, "https://example.com/", "https://example.com/"),
        (_Name, "bob", "bob"),
        (Json[Dict[str, int]], '{"a": 1}', {"a": 1}),
    ],
)
def test_multipart_body_part_type(annotation, value, expected):
    # #1847: only primitive schemas are plain text; everything else is JSON
    api = NinjaAPI()

    def view(request, file: File[UploadedFile], data=Body(...)):
        return {"data": to_jsonable_python(data)}

    view.__annotations__["data"] = annotation
    api.post("/part")(view)

    file = SimpleUploadedFile("test.txt", b"data123")
    response = TestClient(api).post("/part", FILES={"file": file}, POST={"data": value})
    assert response.status_code == 200, response.content
    assert response.json() == {"data": expected}
