from typing import Optional

import pytest
from pydantic import PlainSerializer, computed_field, field_serializer
from typing_extensions import Annotated

from ninja import Field, NinjaAPI, Schema, Status
from ninja.testing import TestAsyncClient, TestClient


class UserOut(Schema):
    name: str


class UserFull(UserOut):
    password: str

    @computed_field  # type: ignore[prop-decorator]
    @property
    def password_hint(self) -> str:
        return self.password[:1]

    @field_serializer("name")
    def upper_name(self, value: str) -> str:
        return value.upper()


class AliasOut(Schema):
    user_name: str = Field(..., alias="userName")


class AliasFull(AliasOut):
    secret: str


class OptOut(Schema):
    name: str
    nick: Optional[str] = None


class OptFull(OptOut):
    token: str = "t0k"


class Wrap(Schema):
    user: UserOut


Redacted = Annotated[UserFull, PlainSerializer(lambda u: {"name": u.name})]

api = NinjaAPI()


@api.get("/subclass", response=UserOut)
def subclass(request):
    return UserFull(name="alice", password="secret")


@api.get("/subclass_status", response={201: UserOut})
def subclass_status(request):
    return Status(201, UserFull(name="alice", password="secret"))


@api.get("/subclass_async", response=UserOut)
async def subclass_async(request):
    return UserFull(name="alice", password="secret")


@api.get("/subclass_alias", response=AliasOut, by_alias=True)
def subclass_alias(request):
    return AliasFull(userName="alice", secret="secret")


@api.get("/subclass_unset", response=OptOut, exclude_unset=True)
def subclass_unset(request):
    return OptFull(name="alice", token="secret")


@api.get("/nested", response=Wrap)
def nested(request):
    return Wrap(user=UserFull(name="alice", password="secret"))


@api.get("/annotated", response=Redacted)
def annotated(request):
    return UserFull(name="alice", password="secret")


client = TestClient(api)


@pytest.mark.parametrize(
    "path,status,expected",
    [
        ("/subclass", 200, {"name": "alice"}),
        ("/subclass_status", 201, {"name": "alice"}),
        ("/subclass_alias", 200, {"userName": "alice"}),
        ("/subclass_unset", 200, {"name": "alice"}),
        ("/nested", 200, {"user": {"name": "alice"}}),
        ("/annotated", 200, {"name": "alice"}),
    ],
)
def test_response_filtered_by_declared_schema(path, status, expected):
    response = client.get(path)
    assert response.status_code == status
    assert response.json() == expected


@pytest.mark.asyncio
async def test_response_filtered_by_declared_schema_async():
    response = await TestAsyncClient(api).get("/subclass_async")
    assert response.status_code == 200
    assert response.json() == {"name": "alice"}
