from datetime import date
from enum import Enum
from typing import Any, Dict, List, Optional, Union

import pytest
from django.core.files.uploadedfile import SimpleUploadedFile
from typing_extensions import Annotated, Literal, TypedDict

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


def test_multipart_structured_body_annotations():
    # https://github.com/vitalik/django-ninja/issues/1847
    from pydantic import Field

    api = NinjaAPI()

    class Item(Schema):
        name: str = "default"

    class Point(TypedDict):
        x: int

    @api.post("/structured")
    def structured(
        request,
        file: UploadedFile = File(...),
        bare_dict: dict = Body(...),
        optional_dict: Optional[Dict[str, int]] = Body(None),
        typed_dict: Point = Body(...),
        annotated_list: Annotated[List[int], Field(min_length=1)] = Body(...),
        anything: Any = Body(...),
        literal_or_model: Union[Literal["none"], Item] = Body(...),
    ):
        return {
            "bare_dict": bare_dict,
            "optional_dict": optional_dict,
            "typed_dict": typed_dict,
            "annotated_list": annotated_list,
            "anything_type": type(anything).__name__,
            "anything": anything,
            "literal_or_model": literal_or_model,
        }

    file = SimpleUploadedFile("test.txt", b"data123")
    response = TestClient(api).post(
        "/structured",
        FILES={"file": file},
        POST={
            "bare_dict": '{"a": 1}',
            "optional_dict": '{"a": 1}',
            "typed_dict": '{"x": 1}',
            "annotated_list": "[1, 2]",
            "anything": '{"a": 1}',
            "literal_or_model": '{"name": "sent"}',
        },
    )
    assert response.status_code == 200, response.content
    assert response.json() == {
        "bare_dict": {"a": 1},
        "optional_dict": {"a": 1},
        "typed_dict": {"x": 1},
        "annotated_list": [1, 2],
        "anything_type": "dict",
        "anything": {"a": 1},
        "literal_or_model": {"name": "sent"},
    }


def test_multipart_annotated_list_validation_still_applies():
    from pydantic import Field

    api = NinjaAPI()

    @api.post("/annotated")
    def annotated(
        request,
        file: UploadedFile = File(...),
        items: Annotated[List[int], Field(min_length=1)] = Body(...),
    ):
        return {"items": items}

    file = SimpleUploadedFile("test.txt", b"data123")
    response = TestClient(api).post(
        "/annotated",
        FILES={"file": file},
        POST={"items": "[]"},
    )
    # the part is parsed as JSON, so Field constraints still apply
    assert response.status_code == 422, response.content
    assert response.json()["detail"][0]["loc"] == ["body", "items"]
