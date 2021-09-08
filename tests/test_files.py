from typing import List

import pytest
from django.core.files.uploadedfile import SimpleUploadedFile
from django.utils.datastructures import MultiValueDict

from ninja import File, NinjaAPI, UploadedFile
from ninja.testing import TestClient

api = NinjaAPI()


@api.post("/file1")
def file1(request, file: UploadedFile = File(...)):
    return {"name": file.name, "data": file.read().decode()}


@api.post("/file2")
def file_no_marker(request, file: UploadedFile):
    return {"name": file.name, "data": file.read().decode()}


@api.post("/file3")
def file_no_marker2(request, file: UploadedFile = None):
    return {"data": file and file.read().decode() or None}


@api.post("/file4")
def file_no_marker4(request, files: List[UploadedFile]):
    return {"result": [f.read().decode() for f in files]}


client = TestClient(api)


def test_files():
    response = client.post("/file1")  # no file
    assert response.status_code == 422

    file = SimpleUploadedFile("test.txt", b"data123")
    response = client.post("/file1", FILES={"file": file})
    assert response.status_code == 200
    assert response.json() == {"name": "test.txt", "data": "data123"}

    file = SimpleUploadedFile("test.txt", b"data345")
    response = client.post("/file2", FILES={"file": file})
    assert response.status_code == 200, response.content
    assert response.json() == {"name": "test.txt", "data": "data345"}

    file = SimpleUploadedFile("test.txt", b"data567")
    response = client.post("/file3")
    assert response.status_code == 200, response.content
    assert response.json() == {"data": None}

    file = SimpleUploadedFile("test.txt", b"data789")
    response = client.post("/file4", FILES=MultiValueDict({"files": [file]}))
    assert response.status_code == 200, response.content
    assert response.json() == {"result": ["data789"]}


def test_schema():
    schema = api.get_openapi_schema()
    methods = []
    for pth in ["/file1", "/file2", "/file3", "/file4"]:
        method = schema["paths"][f"/api{pth}"]["post"]
        method = method["requestBody"]["content"]["multipart/form-data"]["schema"]
        methods.append(method)

    assert methods == [
        {
            "title": "FileParams",
            "type": "object",
            "properties": {
                "file": {"title": "File", "type": "string", "format": "binary"}
            },
            "required": ["file"],
        },
        {
            "title": "FileParams",
            "type": "object",
            "properties": {
                "file": {"title": "File", "type": "string", "format": "binary"}
            },
            "required": ["file"],
        },
        {
            "title": "FileParams",
            "type": "object",
            "properties": {
                "file": {"title": "File", "type": "string", "format": "binary"}
            },
        },
        {
            "title": "FileParams",
            "type": "object",
            "properties": {
                "files": {
                    "title": "Files",
                    "type": "array",
                    "items": {"type": "string", "format": "binary"},
                }
            },
            "required": ["files"],
        },
    ]


def test_invalid_file():
    with pytest.raises(ValueError):
        UploadedFile._validate("not_a_file")
