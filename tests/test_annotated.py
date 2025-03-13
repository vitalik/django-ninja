from typing import List

from typing_extensions import Annotated
from util import pydantic_ref_fix

from ninja import Body, Cookie, Form, Header, NinjaAPI, Path, Query, Schema
from ninja.testing import TestClient

api = NinjaAPI()


class FormData(Schema):
    x: int
    y: float


class Payload(Schema):
    t: int
    p: str


@api.post("/multi/{p}")
def multi_op(
    request,
    q: Annotated[str, Query(description="Query param")],
    p: Annotated[int, Path(description="Path param")],
    f: Annotated[FormData, Form(description="Form params")],
    c: Annotated[str, Cookie(description="Cookie params")],
):
    return {"q": q, "p": p, "f": f.dict(), "c": c}


@api.post("/query_list")
def query_list(
    request,
    q: Annotated[List[str], Query(description="User ID")],
):
    return {"q": q}


@api.post("/headers")
def headers(request, h: Annotated[str, Header()] = "some-default"):
    return {"h": h}


@api.post("/body")
def body_op(
    request, payload: Annotated[Payload, Body(examples=[{"t": 42, "p": "test"}])]
):
    return {"payload": payload}


client = TestClient(api)


def test_multi_op():
    response = client.post("/multi/42?q=1", data={"x": 1, "y": 2}, COOKIES={"c": "3"})
    assert response.status_code == 200, response.content
    assert response.json() == {
        "q": "1",
        "p": 42,
        "f": {"x": 1, "y": 2.0},
        "c": "3",
    }


def test_query_list():
    response = client.post("/query_list?q=1&q=2")
    assert response.status_code == 200, response.content
    assert response.json() == {"q": ["1", "2"]}


def test_body_op():
    response = client.post("/body", json={"t": 42, "p": "test"})
    assert response.status_code == 200, response.content
    assert response.json() == {"payload": {"p": "test", "t": 42}}


def test_headers():
    response = client.post("/headers", headers={"h": "test"})
    assert response.status_code == 200, response.content
    assert response.json() == {"h": "test"}


def test_openapi_schema():
    schema = api.get_openapi_schema()["paths"]
    print(schema)
    assert schema == {
        "/api/multi/{p}": {
            "post": {
                "operationId": "test_annotated_multi_op",
                "summary": "Multi Op",
                "parameters": [
                    {
                        "in": "query",
                        "name": "q",
                        "schema": {
                            "description": "Query param",
                            "title": "Q",
                            "type": "string",
                        },
                        "required": True,
                        "description": "Query param",
                    },
                    {
                        "in": "path",
                        "name": "p",
                        "schema": {
                            "description": "Path param",
                            "title": "P",
                            "type": "integer",
                        },
                        "required": True,
                        "description": "Path param",
                    },
                    {
                        "in": "cookie",
                        "name": "c",
                        "schema": {
                            "description": "Cookie params",
                            "title": "C",
                            "type": "string",
                        },
                        "required": True,
                        "description": "Cookie params",
                    },
                ],
                "responses": {200: {"description": "OK"}},
                "requestBody": {
                    "content": {
                        "application/x-www-form-urlencoded": {
                            "schema": {
                                "title": "FormParams",
                                "type": "object",
                                "properties": {
                                    "x": {"title": "X", "type": "integer"},
                                    "y": {"title": "Y", "type": "number"},
                                },
                                "required": ["x", "y"],
                            }
                        }
                    },
                    "required": True,
                },
            }
        },
        "/api/query_list": {
            "post": {
                "operationId": "test_annotated_query_list",
                "summary": "Query List",
                "parameters": [
                    {
                        "in": "query",
                        "name": "q",
                        "schema": {
                            "description": "User ID",
                            "items": {"type": "string"},
                            "title": "Q",
                            "type": "array",
                        },
                        "required": True,
                        "description": "User ID",
                    }
                ],
                "responses": {200: {"description": "OK"}},
            }
        },
        "/api/headers": {
            "post": {
                "operationId": "test_annotated_headers",
                "summary": "Headers",
                "parameters": [
                    {
                        "in": "header",
                        "name": "h",
                        "schema": {
                            "default": "some-default",
                            "title": "H",
                            "type": "string",
                        },
                        "required": False,
                    }
                ],
                "responses": {200: {"description": "OK"}},
            }
        },
        "/api/body": {
            "post": {
                "operationId": "test_annotated_body_op",
                "summary": "Body Op",
                "parameters": [],
                "responses": {200: {"description": "OK"}},
                "requestBody": {
                    "content": {
                        "application/json": {
                            "schema": pydantic_ref_fix({
                                "$ref": "#/components/schemas/Payload",
                                "examples": [{"p": "test", "t": 42}],
                            })
                        }
                    },
                    "required": True,
                },
            }
        },
    }
