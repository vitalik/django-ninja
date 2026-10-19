import pytest
from django.core.files.uploadedfile import SimpleUploadedFile

from ninja import Body, File, Form, NinjaAPI, UploadedFile
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
    "value", ['say "hi"', "5'10\"", '"quoted"', "line1\nline2", "a\\nb", ""]
)
def test_multipart_body_str_is_passed_unchanged(value):
    api = NinjaAPI()

    @api.post("/m")
    def m(request, s: str = Body(...), f: str = Form("d")):
        return {"s": s}

    response = TestClient(api).post("/m", data={"s": value, "f": "a"})
    assert response.status_code == 200, response.content
    assert response.json() == {"s": value}


def test_multipart_body_str_alongside_non_str_field():
    api = NinjaAPI()

    @api.post("/m")
    def m(request, s: str = Body(...), n: int = Body(...)):
        return {"s": s, "n": n}

    response = TestClient(api).post("/m", data={"s": '5\'10"', "n": "42"})
    assert response.status_code == 200, response.content
    assert response.json() == {"s": '5\'10"', "n": 42}
