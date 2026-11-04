"""
Schema instances returned inside a response (list items, nested fields, ...) are
re-validated against the declared response schema: resolvers run with the request
context and values that never went through validation are filtered out.
"""

import warnings
from typing import Dict, List, Optional

import pytest

from ninja import NinjaAPI, Schema
from ninja.pagination import paginate
from ninja.streaming import JSONL
from ninja.testing import TestAsyncClient, TestClient


class Contact(Schema):
    email: str

    @staticmethod
    def resolve_email(obj, context):
        if context and context.get("request"):
            return "[hidden]"
        return obj["email"] if isinstance(obj, dict) else obj.email


class Profile(Schema):
    bio: str


class UserOut(Schema):
    id: int
    profile: Profile


class Wrap(Schema):
    user: UserOut


SECRET_PROFILE = {"bio": "hi", "password_hash": "secret"}


def unvalidated_user() -> UserOut:
    user = UserOut(id=1, profile=Profile(bio="x"))
    user.profile = dict(SECRET_PROFILE)  # no validate_assignment -> stays a dict
    return user


def constructed_user() -> UserOut:
    return UserOut.model_construct(id=2, profile=dict(SECRET_PROFILE))


api = NinjaAPI()


@api.get("/contacts", response=List[Contact])
def contacts(request):
    return [Contact(email="private@example.com")]


@api.get("/list", response=List[UserOut])
def users_list(request):
    return [unvalidated_user(), constructed_user()]


@api.get("/optional", response=Optional[UserOut])
def users_optional(request):
    return constructed_user()


@api.get("/dict", response=Dict[str, UserOut])
def users_dict(request):
    return {"u": constructed_user()}


@api.get("/nested", response=Wrap)
def users_nested(request):
    return {"user": constructed_user()}


@api.get("/paginated", response=List[UserOut])
@paginate
def users_paginated(request):
    return [unvalidated_user(), constructed_user()]


@api.get("/stream", response=JSONL[UserOut])
def users_stream(request):
    yield unvalidated_user()
    yield constructed_user()


@api.get("/async-list", response=List[UserOut])
async def users_async_list(request):
    return [constructed_user()]


client = TestClient(api)

EXPECTED_USERS = [
    {"id": 1, "profile": {"bio": "hi"}},
    {"id": 2, "profile": {"bio": "hi"}},
]


@pytest.fixture(autouse=True)
def _ignore_serializer_warnings():
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", UserWarning)
        yield


def test_nested_instances_resolvers_get_request_context():
    assert client.get("/contacts").json() == [{"email": "[hidden]"}]


def test_list_items_are_revalidated():
    assert client.get("/list").json() == EXPECTED_USERS


def test_optional_instance_is_revalidated():
    assert client.get("/optional").json() == EXPECTED_USERS[1]


def test_dict_values_are_revalidated():
    assert client.get("/dict").json() == {"u": EXPECTED_USERS[1]}


def test_nested_instance_is_revalidated():
    assert client.get("/nested").json() == {"user": EXPECTED_USERS[1]}


def test_paginated_items_are_revalidated():
    assert client.get("/paginated").json() == {"items": EXPECTED_USERS, "count": 2}


def test_streamed_items_are_revalidated():
    response = client.get("/stream")
    lines = [line for line in response.content.decode().splitlines() if line]
    assert len(lines) == 2
    assert "password_hash" not in response.content.decode()


@pytest.mark.asyncio
async def test_async_list_items_are_revalidated():
    async_client = TestAsyncClient(api)
    response = await async_client.get("/async-list")
    assert response.json() == [EXPECTED_USERS[1]]
