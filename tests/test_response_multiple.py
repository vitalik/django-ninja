from typing import List, Union

import pytest
from pydantic import ValidationError

from ninja import NinjaAPI, Schema
from ninja.errors import ConfigError, HttpError
from ninja.responses import codes_2xx, codes_3xx
from ninja.testing import TestClient

api = NinjaAPI()


class RequestErrorResponse(Schema):
    detail: str
    reason: list[str]


class ServerErrorResponse(Schema):
    detail: str


class BasicHttpError(HttpError): ...


class RequestError(HttpError[RequestErrorResponse]):
    status_code = 400
    message = "Request Error"


class ServerError(HttpError[ServerErrorResponse]):
    status_code = 500
    message = "Server Error"


@api.get("/check_int", response={200: int})
def check_int(request):
    return 200, "1"


@api.get("/check_int2", response={200: int})
def check_int2(request):
    return 200, "str"


@api.get("/check_single_with_status", response=int)
def check_single_with_status(request, code: int):
    return code, 1


@api.get("/check_response_schema", response={400: int})
def check_response_schema(request):
    return 200, 1


@api.get("/check_no_content", response={204: None})
def check_no_content(request, return_code: bool):
    if return_code:
        return 204, None
    return  # None


@api.get(
    "/check_multiple_codes",
    response={codes_2xx: int, codes_3xx: str, ...: float},
)
def check_multiple_codes(request, code: int):
    return code, "1"


@api.get(
    "/excs_in_responses",
    response={codes_2xx: str, 400: RequestError, 404: BasicHttpError, 500: ServerError},
)
def excs_in_responses(request, code: int):
    if code == 400:
        raise RequestError
    if code == 500:
        raise ServerError
    return code, "1"


@api.get(
    "/errors_in_docstring",
    # response={400: RequestError, 500: ServerError},  # <-- not needed
)
def errors_in_docstring(request, code: int):
    """
    Raises:
        RequestError: you made a mistake in the request
        ServerError: unexpected error on our server
    """
    if code == 400:
        raise RequestError
    if code == 500:
        raise ServerError
    return code, "1"


class User:
    def __init__(self, id, name, password):
        self.id = id
        self.name = name
        self.password = password


class UserModel(Schema):
    id: int
    name: str
    # skipping password output to responses


class ErrorModel(Schema):
    detail: str


@api.get("/check_model", response={200: UserModel, 202: UserModel})
def check_model(request):
    return 202, User(1, "John", "Password")


@api.get("/check_list_model", response={200: List[UserModel]})
def check_list_model(request):
    return 200, [User(1, "John", "Password")]


@api.get("/check_union", response={200: Union[int, UserModel], 400: ErrorModel})
def check_union(request, q: int):
    if q == 0:
        return 200, 1
    if q == 1:
        return 200, User(1, "John", "Password")
    if q == 2:
        return 400, {"detail": "error"}
    return "invalid"


client = TestClient(api)


@pytest.fixture
def schema():
    return api.get_openapi_schema()


@pytest.mark.parametrize(
    "path,expected_status,expected_response",
    [
        ("/check_int", 200, 1),
        ("/check_single_with_status?code=200", 200, 1),
        ("/check_model", 202, {"id": 1, "name": "John"}),  # ! the password is skipped
        ("/check_list_model", 200, [{"id": 1, "name": "John"}]),
        ("/check_union?q=0", 200, 1),
        ("/check_union?q=1", 200, {"id": 1, "name": "John"}),
        ("/check_union?q=2", 400, {"detail": "error"}),
        ("/check_multiple_codes?code=200", 200, 1),
        ("/check_multiple_codes?code=201", 201, 1),
        ("/check_multiple_codes?code=202", 202, 1),
        ("/check_multiple_codes?code=206", 206, 1),
        ("/check_multiple_codes?code=300", 300, "1"),
        ("/check_multiple_codes?code=308", 308, "1"),
        ("/check_multiple_codes?code=400", 400, 1.0),
        ("/check_multiple_codes?code=500", 500, 1.0),
    ],
)
def test_responses(path, expected_status, expected_response):
    response = client.get(path)
    assert response.status_code == expected_status, response.content
    assert response.json() == expected_response


def test_schema(schema):
    checks = [
        ("/api/check_int", {200}),
        ("/api/check_int2", {200}),
        ("/api/check_single_with_status", {200}),
        ("/api/check_response_schema", {400}),
        ("/api/check_model", {200, 202}),
        ("/api/check_list_model", {200}),
        ("/api/check_union", {200, 400}),
    ]
    schema = api.get_openapi_schema()

    # checking codes
    for path, codes in checks:
        responses = schema["paths"][path]["get"]["responses"]
        responses_codes = set(responses.keys())
        assert codes == responses_codes, f"{codes} != {responses_codes}"

    # checking model
    check_model_responses = schema["paths"]["/api/check_model"]["get"]["responses"]

    assert check_model_responses == {
        200: {
            "content": {
                "application/json": {
                    "schema": {"$ref": "#/components/schemas/UserModel"}
                }
            },
            "description": "OK",
        },
        202: {
            "content": {
                "application/json": {
                    "schema": {"$ref": "#/components/schemas/UserModel"}
                }
            },
            "description": "Accepted",
        },
    }


def test_excs_as_responses(schema):
    responses = schema["paths"]["/api/excs_in_responses"]["get"]["responses"]
    schemas = schema["components"]["schemas"]

    assert responses == {
        200: {
            "content": {
                "application/json": {"schema": {"title": "Response", "type": "string"}}
            },
            "description": "OK",
        },
        201: {
            "content": {
                "application/json": {"schema": {"title": "Response", "type": "string"}}
            },
            "description": "Created",
        },
        202: {
            "content": {
                "application/json": {"schema": {"title": "Response", "type": "string"}}
            },
            "description": "Accepted",
        },
        203: {
            "content": {
                "application/json": {"schema": {"title": "Response", "type": "string"}}
            },
            "description": "Non-Authoritative Information",
        },
        204: {
            "content": {
                "application/json": {"schema": {"title": "Response", "type": "string"}}
            },
            "description": "No Content",
        },
        205: {
            "content": {
                "application/json": {"schema": {"title": "Response", "type": "string"}}
            },
            "description": "Reset Content",
        },
        206: {
            "content": {
                "application/json": {"schema": {"title": "Response", "type": "string"}}
            },
            "description": "Partial Content",
        },
        400: {
            "content": {
                "application/json": {
                    "schema": {"$ref": "#/components/schemas/RequestErrorResponse"}
                }
            },
            "description": "Bad Request",
        },
        404: {
            "content": {
                "application/json": {
                    "schema": {"$ref": "#/components/schemas/HttpErrorResponse"}
                }
            },
            "description": "Not Found",
        },
        500: {
            "content": {
                "application/json": {
                    "schema": {"$ref": "#/components/schemas/ServerErrorResponse"}
                }
            },
            "description": "Internal Server Error",
        },
    }

    assert "RequestErrorResponse" in schemas
    assert "HttpErrorResponse" in schemas
    assert "ServerErrorResponse" in schemas

    assert schemas["RequestErrorResponse"] == {
        "properties": {
            "detail": {"title": "Detail", "type": "string"},
            "reason": {"items": {"type": "string"}, "title": "Reason", "type": "array"},
        },
        "required": ["detail", "reason"],
        "title": "RequestErrorResponse",
        "type": "object",
    }
    assert schemas["HttpErrorResponse"] == {
        "properties": {"detail": {"title": "Detail", "type": "string"}},
        "required": ["detail"],
        "title": "HttpErrorResponse",
        "type": "object",
    }
    assert schemas["ServerErrorResponse"] == {
        "properties": {"detail": {"title": "Detail", "type": "string"}},
        "required": ["detail"],
        "title": "ServerErrorResponse",
        "type": "object",
    }


def test_no_content():
    response = client.get("/check_no_content?return_code=1")
    assert response.status_code == 204
    assert response.content == b""

    response = client.get("/check_no_content?return_code=0")
    assert response.status_code == 204
    assert response.content == b""

    schema = api.get_openapi_schema()
    details = schema["paths"]["/api/check_no_content"]["get"]["responses"]
    assert details == {204: {"description": "No Content"}}


def test_validates():
    with pytest.raises(ValidationError):
        client.get("/check_int2")

    with pytest.raises(ValidationError):
        client.get("/check_union?q=3")

    with pytest.raises(ConfigError):
        client.get("/check_response_schema")

    with pytest.raises(ConfigError):
        client.get("/check_single_with_status?code=300")
