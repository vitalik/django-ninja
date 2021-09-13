import pytest

from ninja import Form, NinjaAPI, Schema
from ninja.errors import ConfigError
from ninja.testing import TestClient

api = NinjaAPI()


@api.post("/form")
def form_operation(request, s: str = Form(...), i: int = Form(None)):
    return {"s": s, "i": i}


client = TestClient(api)


def test_form():
    response = client.post("/form")  # invalid
    assert response.status_code == 422

    response = client.post("/form", POST={"s": "text"})
    assert response.status_code == 200
    assert response.json() == {"i": None, "s": "text"}

    response = client.post("/form", POST={"s": "text", "i": None})
    assert response.status_code == 200
    assert response.json() == {"i": None, "s": "text"}

    response = client.post("/form", POST={"s": "text", "i": 2})
    assert response.status_code == 200
    assert response.json() == {"i": 2, "s": "text"}


def test_schema():
    schema = api.get_openapi_schema()
    method = schema["paths"]["/api/form"]["post"]
    assert method["requestBody"] == {
        "content": {
            "application/x-www-form-urlencoded": {
                "schema": {
                    "properties": {
                        "i": {"title": "I", "type": "integer"},
                        "s": {"title": "S", "type": "string"},
                    },
                    "required": ["s"],
                    "title": "FormParams",
                    "type": "object",
                }
            }
        },
        "required": True,
    }


def test_duplicate_names():
    class TestData(Schema):
        p1: str

    match = "Duplicated name: 'p1' in params: 'p1' & 'data'"
    with pytest.raises(ConfigError, match=match):

        @api.post("/broken1")
        def broken1(request, p1: int = Form(...), data: TestData = Form(...)):
            pass

    match = "Duplicated name: 'p1' also in 'data'"
    with pytest.raises(ConfigError, match=match):

        @api.post("/broken2")
        def broken2(request, data: TestData = Form(...), p1: int = Form(...)):
            pass


# TODO: Fix schema for this case:
# class Credentials(Schema):
#     username: str
#     password: str


# @api.post("/login")
# def login(request, credentials: Credentials = Form(...)):
#     return {'username': credentials.username}
