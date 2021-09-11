import pytest
from django.core.files.uploadedfile import SimpleUploadedFile

from ninja import Body, File, Form, NinjaAPI, UploadedFile
from ninja.main import ConfigError
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
                    "title": "FormParams",
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


def test_mix():
    api2 = NinjaAPI()

    @api2.post("/test")
    def mix(request, data: str = Body(...), form: str = Form(...)):
        pass

    with pytest.raises(ConfigError):
        api2.get_openapi_schema()
