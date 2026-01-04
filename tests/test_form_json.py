import json
from typing import List

from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import override_settings

from ninja import NinjaAPI, Schema, UploadedFile
from ninja.params import FormJson
from ninja.testing import TestClient

api = NinjaAPI()


class Metadata(Schema):
    source: str
    tags: List[str] = []


@api.post("/upload")
def upload_with_metadata(request, file: UploadedFile, metadata: FormJson[Metadata]):
    return {
        "filename": file.name,
        "source": metadata.source,
        "tags": metadata.tags,
    }


@api.post("/metadata-only")
def metadata_only(request, metadata: FormJson[Metadata]):
    return {"source": metadata.source, "tags": metadata.tags}


client = TestClient(api)


def test_form_json_basic():
    metadata = json.dumps({"source": "camera", "tags": ["photo", "vacation"]})
    response = client.post("/metadata-only", POST={"metadata": metadata})
    assert response.status_code == 200
    assert response.json() == {"source": "camera", "tags": ["photo", "vacation"]}


def test_form_json_with_file():
    metadata = json.dumps({"source": "upload"})
    file = SimpleUploadedFile("test.txt", b"content")
    response = client.post(
        "/upload",
        POST={"metadata": metadata},
        FILES={"file": file},
    )
    assert response.status_code == 200
    assert response.json()["source"] == "upload"
    assert response.json()["filename"] == "test.txt"


def test_form_json_invalid_json():
    response = client.post("/metadata-only", POST={"metadata": "not valid json"})
    assert response.status_code == 400


def test_form_json_validation_error():
    # Missing required field 'source'
    metadata = json.dumps({"tags": ["tag1"]})
    response = client.post("/metadata-only", POST={"metadata": metadata})
    assert response.status_code == 422


def test_form_json_default_values():
    metadata = json.dumps({"source": "test"})
    response = client.post("/metadata-only", POST={"metadata": metadata})
    assert response.status_code == 200
    assert response.json()["tags"] == []  # default value


def test_form_json_missing_field():
    # FormJson field not provided in POST - covers branch where name not in request.POST
    response = client.post("/metadata-only", POST={})
    assert response.status_code == 422


@override_settings(DEBUG=True)
def test_form_json_invalid_json_debug_mode():
    # Invalid JSON with DEBUG=True shows error details
    response = client.post("/metadata-only", POST={"metadata": "not valid json"})
    assert response.status_code == 400
    assert "Expecting value" in response.json()["detail"]  # JSON parse error detail
