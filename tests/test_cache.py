import time
from time import sleep

import pytest
from pydantic import BaseModel

from ninja import Router, NinjaAPI
from ninja.testing import TestClient

api = NinjaAPI(
    cache=True,
    cache_timeout=3,
)


class User(BaseModel):
    username: str
    email: str


user = User(
    username="ninjadev",
    email="ninja@ninja.dev",
)


@api.get("/user", response=User, cache=True)
def get_user(request):
    return user


@api.get("/change-user", response=User)
def change_user(request):
    user.username += "_changed"
    return user


@api.get("/sleep", response=str)
def sleep(request):
    time.sleep(4)
    return "done"


client = TestClient(api)


@pytest.mark.parametrize(
    "path,expected_result",
    [
        ("/user", {"username": "ninjadev", "email": "ninja@ninja.dev"}),
        ("/change-user", {"username": "ninjadev_changed", "email": "ninja@ninja.dev"}),
        ("/user", {"username": "ninjadev", "email": "ninja@ninja.dev"}),
        ("/sleep", "done"),
        ("/user", {"username": "ninjadev_changed", "email": "ninja@ninja.dev"}),
    ]
)
def test_cache_responses(path, expected_result):
    response = client.get(path)
    assert response.status_code == 200, response.content
    assert response.json() == expected_result
