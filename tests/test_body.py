from typing import Any, Dict, List

import pytest
from pydantic import field_validator

from ninja import Body, Form, NinjaAPI, Schema
from ninja.errors import ConfigError, ValidationError, ValidationErrorContext
from ninja.testing import TestClient

api = NinjaAPI()

# testing Body marker:


@api.post("/task")
def create_task(request, start: int = Body(...), end: int = Body(...)):
    return [start, end]


@api.post("/task2")
def create_task2(request, start: int = Body(2), end: int = Form(1)):
    return [start, end]


class UserIn(Schema):
    # for testing validation errors context
    email: str

    @field_validator("email")
    @classmethod
    def validate_email(cls, v):
        if "@" not in v:
            raise ValueError("invalid email")
        return v


@api.post("/users")
def create_user(request, payload: UserIn):
    return payload.dict()


client = TestClient(api)


def test_body():
    assert client.post("/task", json={"start": 1, "end": 2}).json() == [1, 2]
    assert client.post("/task", json={"start": 1}).json() == {
        "detail": [{"type": "missing", "loc": ["body", "end"], "msg": "Field required"}]
    }


def test_body_form():
    data = client.post("/task2", POST={"start": "1", "end": "2"}).json()
    print(data)
    assert client.post("/task2", POST={"start": "1", "end": "2"}).json() == [1, 2]
    assert client.post("/task2").json() == [2, 1]


def test_body_validation_error():
    resp = client.post("/users", json={"email": "valid@email.com"})
    assert resp.status_code == 200

    resp = client.post("/users", json={"email": "invalid.com"})
    assert resp.status_code == 422
    assert resp.json()["detail"] == [
        {
            "type": "value_error",
            "loc": ["body", "payload", "email"],
            "msg": "Value error, invalid email",
            "ctx": {"error": "invalid email"},
        }
    ]


def test_incorrect_annotation():
    api = NinjaAPI()

    class Some(Schema):
        a: int

    with pytest.raises(ConfigError):

        @api.post("/some")
        def some(request, payload=Some):
            #  ................. ^------ invalid usage assigning class instead of annotation
            return 42


class CustomErrorAPI(NinjaAPI):
    def validation_error_from_error_contexts(
        self,
        error_contexts: List[ValidationErrorContext],
    ) -> ValidationError:
        errors: List[Dict[str, Any]] = []
        for context in error_contexts:
            model = context.model
            for e in context.pydantic_validation_error.errors(
                include_url=False, include_context=False, include_input=False
            ):
                errors.append({
                    "source": model.__ninja_param_source__,
                    "message": e["msg"],
                })
        return ValidationError(errors)


custom_error_api = CustomErrorAPI()


@custom_error_api.post("/users")
def create_user2(request, payload: UserIn):
    return payload.dict()


custom_error_client = TestClient(custom_error_api)


def test_body_custom_validation_error():
    resp = custom_error_client.post("/users", json={"email": "valid@email.com"})
    assert resp.status_code == 200

    resp = custom_error_client.post("/users", json={"email": "invalid.com"})
    assert resp.status_code == 422
    assert resp.json()["detail"] == [
        {
            "source": "body",
            "message": "Value error, invalid email",
        }
    ]
