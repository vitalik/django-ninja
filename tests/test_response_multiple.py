from ninja import responses
from ninja.errors import ConfigError
import pytest
from pydantic import ValidationError, BaseModel
from ninja import Router
from client import NinjaClient
from typing import List, Union


router = Router()


# TODO: Return annotaion is not good
# results are not always matching the type
# and long functions will be even longer/unreadable...


@router.get("/check_int", response={200: int})
def check_int(request):
    return 200, "1"


@router.get("/check_int2", response={200: int})
def check_int2(request):
    return 200, "str"


@router.get("/check_single_with_status", response=int)
def check_single_with_status(request):
    return 302, 1


@router.get("/check_response_schema", response={400: int})
def check_response_schema(request):
    return 200, 1


class User:
    def __init__(self, id, name, password):
        self.id = id
        self.name = name
        self.password = password


class UserModel(BaseModel):
    id: int
    name: str
    # skipping password output to responses

    class Config:
        orm_mode = True


class ErrorModel(BaseModel):
    detail: str


@router.get("/check_model", response={200: UserModel, 202: UserModel})
def check_model(request):
    return 202, User(1, "John", "Password")


@router.get("/check_list_model", response={200: List[UserModel]})
def check_list_model(request):
    return 200, [User(1, "John", "Password")]


@router.get("/check_union", response={200: Union[int, UserModel], 400: ErrorModel})
def check_union(request, q: int):
    if q == 0:
        return 200, 1
    if q == 1:
        return 200, User(1, "John", "Password")
    if q == 2:
        return 400, {"detail": "error"}
    return "invalid"


client = NinjaClient(router)


@pytest.mark.parametrize(
    "path,expected_status,expected_response",
    [
        ("/check_int", 200, 1),
        ("/check_single_with_status", 302, 1),
        ("/check_model", 202, {"id": 1, "name": "John"}),  # the password is skipped
        (
            "/check_list_model",
            200,
            [{"id": 1, "name": "John"}],
        ),  # the password is skipped
        ("/check_union?q=0", 200, 1),
        ("/check_union?q=1", 200, {"id": 1, "name": "John"}),
        ("/check_union?q=2", 400, {"detail": "error"}),
    ],
)
def test_responses(path, expected_status, expected_response):
    response = client.get(path)
    assert response.status_code == expected_status, response.content
    assert response.json() == expected_response


def test_validates():
    with pytest.raises(ValidationError):
        client.get("/check_int2")

    with pytest.raises(ValidationError):
        client.get("/check_union?q=3")

    with pytest.raises(ConfigError):
        client.get("/check_response_schema")
