from typing import List, Union

import pytest
from django.http import HttpResponse
from pydantic import BaseModel, ValidationError

from ninja import Router
from ninja.testing import TestClient

router = Router()


@router.get("/check_int", response=int)
def check_int(request):
    return "1"


@router.get("/check_int2", response=int)
def check_int2(request):
    return "str"


class User:
    def __init__(self, id, user_name, password):
        self.id = id
        self.user_name = user_name
        self.password = password


def to_camel(string: str) -> str:
    return "".join(word.capitalize() for word in string.split("_"))


class UserModel(BaseModel):
    id: int
    user_name: str
    # skipping password output to responses

    class Config:
        orm_mode = True
        alias_generator = to_camel
        allow_population_by_field_name = True


@router.get("/check_model", response=UserModel)
def check_model(request):
    return User(1, "John", "Password")


@router.get("/check_list_model", response=List[UserModel])
def check_list_model(request):
    return [User(1, "John", "Password")]


@router.get("/check_model_alias", response=UserModel, by_alias=True)
def check_model_alias(request):
    return User(1, "John", "Password")


@router.get("/check_union", response=Union[int, UserModel])
def check_union(request, q: int):
    if q == 0:
        return 1
    if q == 1:
        return User(1, "John", "Password")
    return "invalid"


@router.get("/check_set_header")
def check_set_header(request, response: HttpResponse):
    response["Cache-Control"] = "no-cache"
    return 1


@router.get("/check_set_cookie")
def check_set_cookie(request, set: bool, response: HttpResponse):
    if set:
        response.set_cookie("test", "me")
    return 1


@router.get("/check_del_cookie")
def check_del_cookie(request, response: HttpResponse):
    response.delete_cookie("test")
    return 1


client = TestClient(router)


@pytest.mark.parametrize(
    "path,expected_response",
    [
        ("/check_int", 1),
        ("/check_model", {"id": 1, "user_name": "John"}),  # the password is skipped
        (
            "/check_list_model",
            [{"id": 1, "user_name": "John"}],
        ),  # the password is skipped
        ("/check_model", {"id": 1, "user_name": "John"}),  # the password is skipped
        ("/check_model_alias", {"Id": 1, "UserName": "John"}),  # result is Camal Case
        ("/check_union?q=0", 1),
        ("/check_union?q=1", {"id": 1, "user_name": "John"}),
    ],
)
def test_responses(path, expected_response):
    response = client.get(path)
    assert response.status_code == 200, response.content
    assert response.json() == expected_response


def test_validates():
    with pytest.raises(ValidationError):
        client.get("/check_int2")

    with pytest.raises(ValidationError):
        client.get("/check_union?q=2")


def test_set_header():
    response = client.get("/check_set_header")
    assert response.status_code == 200
    assert response.content == b"1"
    assert response["Cache-Control"] == "no-cache"


def test_set_cookie():
    response = client.get("/check_set_cookie?set=0")
    assert "test" not in response.cookies

    response = client.get("/check_set_cookie?set=1")
    cookie = response.cookies.get("test")
    assert cookie
    assert cookie.value == "me"


def test_del_cookie():
    response = client.get("/check_del_cookie")
    cookie = response.cookies.get("test")
    assert cookie
    assert cookie["expires"] == "Thu, 01 Jan 1970 00:00:00 GMT"
    assert cookie["max-age"] == 0
