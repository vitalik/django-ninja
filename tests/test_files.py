import importlib
import re
from typing import List

import pytest
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import override_settings
from django.test.client import MULTIPART_CONTENT
from django.utils.datastructures import MultiValueDict

from ninja import File, NinjaAPI, UploadedFile
from ninja.compatibility.files import fix_request_files_middleware
from ninja.errors import ConfigError
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


@api.post("/file5")
def file_no_marker5(request, file1: UploadedFile, file2: UploadedFile):
    return {"result": [f.read().decode() for f in (file1, file2)]}


@api.post("/file6")
def file_no_marker6(request, file: UploadedFile, files: List[UploadedFile]):
    return {"result": [f.read().decode() for f in [file] + files]}


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

    file1 = SimpleUploadedFile("test1.txt", b"dataABC")
    file2 = SimpleUploadedFile("test2.txt", b"dataDEF")
    response = client.post("/file5", FILES={"file1": file1, "file2": file2})
    assert response.status_code == 200, response.content
    assert response.json() == {"result": ["dataABC", "dataDEF"]}

    file1 = SimpleUploadedFile("test1.txt", b"dataABC")
    file2 = SimpleUploadedFile("test2.txt", b"dataDEF")
    file3 = SimpleUploadedFile("test2.txt", b"dataGHI")
    response = client.post(
        "/file6", FILES=MultiValueDict({"file": [file1], "files": [file2, file3]})
    )
    assert response.status_code == 200, response.content
    assert response.json() == {"result": ["dataABC", "dataDEF", "dataGHI"]}


def test_schema():
    schema = api.get_openapi_schema()
    methods = []
    for pth in ["/file1", "/file2", "/file3", "/file4"]:
        method = schema["paths"][f"/api{pth}"]["post"]
        method = method["requestBody"]["content"]["multipart/form-data"]["schema"]
        methods.append(method)

    assert methods == [
        {
            "type": "object",
            "properties": {
                "file": {"type": "string", "format": "binary", "title": "File"}
            },
            "required": ["file"],
            "title": "FileParams",
        },
        {
            "type": "object",
            "properties": {
                "file": {"type": "string", "format": "binary", "title": "File"}
            },
            "required": ["file"],
            "title": "FileParams",
        },
        {
            "type": "object",
            "properties": {
                "file": {"type": "string", "format": "binary", "title": "File"}
            },
            "title": "FileParams",
        },
        {
            "type": "object",
            "properties": {
                "files": {
                    "type": "array",
                    "items": {"type": "string", "format": "binary"},
                    "title": "Files",
                }
            },
            "required": ["files"],
            "title": "FileParams",
        },
    ]


def test_invalid_file():
    with pytest.raises(ValueError):
        UploadedFile._validate("not_a_file", None)


def test_files_fix_middleware():
    api = NinjaAPI()

    with pytest.raises(ConfigError):

        @api.patch("/file1")
        def patch_with_file(request, file: UploadedFile):
            return {"name": file.name}


@override_settings(NINJA_FIX_REQUEST_FILES_URLS=re.compile(r"^/file\d+"))
def test_files_fix_middleware_urls(rf):
    def get_response(request):
        assert request.FILES == {}

    from ninja import conf
    from ninja.compatibility import files

    importlib.reload(conf)
    importlib.reload(files)

    file = SimpleUploadedFile("test.txt", b"data123")
    post_data = rf._encode_data({"file": file}, MULTIPART_CONTENT)
    request = rf.generic(
        "PATCH", "/not-patched", post_data, content_type=MULTIPART_CONTENT
    )

    fix_request_files_middleware(get_response)(request)
