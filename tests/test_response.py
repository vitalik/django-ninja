import pytest
from pydantic import ValidationError, BaseModel
from ninja import Router
from client import NinjaClient
from typing import List, Union


router = Router()


# TODO: Return annotaion is not good
# results are not always matching the type
# and long functions will be even longer/unreadable...


@router.get("/check_int")
def check_int(request) -> int:
    return "1"


@router.get("/check_int2")
def check_int2(request) -> int:
    return "str"


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


@router.get("/check_model")
def check_model(request) -> UserModel:
    return User(1, "John", "Password")


@router.get("/check_model_ref")
def check_model_ref(request) -> "UserModel":
    return User(1, "John", "Password")


@router.get("/check_list_model")
def check_list_model(request) -> List[UserModel]:
    return [User(1, "John", "Password")]


@router.get("/check_union")
def check_union(request, q: int) -> Union[int, UserModel]:
    if q == 0:
        return 1
    if q == 1:
        return User(1, "John", "Password")
    return "invalid"


client = NinjaClient(router)


@pytest.mark.parametrize(
    "path,expected_response",
    [
        ("/check_int", 1),
        ("/check_model", {"id": 1, "name": "John"}),
        ("/check_model_ref", {"id": 1, "name": "John"}),  # the password is skipped
        ("/check_list_model", [{"id": 1, "name": "John"}]),  # the password is skipped
        ("/check_union?q=0", 1),
        ("/check_union?q=1", {"id": 1, "name": "John"}),
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
