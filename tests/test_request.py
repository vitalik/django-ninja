from typing import Optional

import pytest
from pydantic import ConfigDict

from ninja import Body, Cookie, Header, Router, Schema
from ninja.testing import TestClient


class OptionalEmptySchema(Schema):
    model_config = ConfigDict(extra="forbid")
    name: Optional[str] = None


class ExtraForbidSchema(Schema):
    model_config = ConfigDict(extra="forbid")
    name: str
    metadata: Optional[OptionalEmptySchema] = None


router = Router()


@router.get("/headers1")
def headers1(request, user_agent: str = Header(...)):
    return user_agent


@router.get("/headers2")
def headers2(request, ua: str = Header(..., alias="User-Agent")):
    return ua


@router.get("/headers3")
def headers3(request, content_length: int = Header(...)):
    return content_length


@router.get("/headers4")
def headers4(request, c_len: int = Header(..., alias="Content-length")):
    return c_len


@router.get("/headers5")
def headers5(request, missing: int = Header(...)):
    return missing


@router.get("/cookies1")
def cookies1(request, weapon: str = Cookie(...)):
    return weapon


@router.get("/cookies2")
def cookies2(request, wpn: str = Cookie(..., alias="weapon")):
    return wpn


@router.post("/test-schema")
def schema(request, payload: ExtraForbidSchema = Body(...)):
    return "ok"


client = TestClient(router)


@pytest.mark.parametrize(
    "path,expected_status,expected_response",
    [
        ("/headers1", 200, "Ninja"),
        ("/headers2", 200, "Ninja"),
        ("/headers3", 200, 10),
        ("/headers4", 200, 10),
        (
            "/headers5",
            422,
            {
                "detail": [
                    {
                        "type": "missing",
                        "loc": ["header", "missing"],
                        "msg": "Field required",
                    }
                ]
            },
        ),
        ("/cookies1", 200, "shuriken"),
        ("/cookies2", 200, "shuriken"),
    ],
)
def test_headers(path, expected_status, expected_response):
    response = client.get(
        path,
        headers={"User-Agent": "Ninja", "Content-Length": "10"},
        COOKIES={"weapon": "shuriken"},
    )
    assert response.status_code == expected_status, response.content
    print(response.json())
    assert response.json() == expected_response


@pytest.mark.parametrize(
    "path,json,expected_status,expected_response",
    [
        (
            "/test-schema",
            {"name": "test", "extra_name": "test2"},
            422,
            {
                "detail": [
                    {
                        "type": "extra_forbidden",
                        "loc": ["body", "payload", "extra_name"],
                        "msg": "Extra inputs are not permitted",
                    }
                ]
            },
        ),
        (
            "/test-schema",
            {"name": "test", "metadata": {"extra_name": "xxx"}},
            422,
            {
                "detail": [
                    {
                        "loc": ["body", "payload", "metadata", "extra_name"],
                        "msg": "Extra inputs are not permitted",
                        "type": "extra_forbidden",
                    }
                ]
            },
        ),
        (
            "/test-schema",
            {"name": "test", "metadata": "test2"},
            422,
            {
                "detail": [
                    {
                        "type": "model_attributes_type",
                        "loc": ["body", "payload", "metadata"],
                        "msg": "Input should be a valid dictionary or object to extract fields from",
                    }
                ]
            },
        ),
    ],
)
def test_pydantic_config(path, json, expected_status, expected_response):
    # test extra forbid
    response = client.post(path, json=json)
    assert response.json() == expected_response
    assert response.status_code == expected_status
