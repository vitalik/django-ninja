from collections import Counter
from typing import List, Union

import pytest
from django.core.cache import cache
from django.http.response import HttpResponse as HttpResponseDjango, HttpResponseBase
from django.utils.cache import learn_cache_key
from pydantic import BaseModel

from ninja import Router
from ninja.cache import cache_page
from ninja.testing import TestClient

router = Router()

views_calls = Counter()


@router.get("/check_int", response=int)
@cache_page()
def check_int(request):
    views_calls["/check_int"] += 1
    return "1"


@router.get("/check_int_cache_key", response=int)
@cache_page(key_prefix="custom_cache_key")
def check_int_cache_key(request):
    views_calls["custom_cache_key"] += 1
    return "1"


@router.get("/check_int2", response=int)
@cache_page()
def check_int2(request):
    views_calls["/check_int2"] += 1
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
@cache_page()
def check_model(request):
    views_calls["/check_model"] += 1
    return User(1, "John", "Password")


@router.get("/check_list_model", response=List[UserModel])
@cache_page()
def check_list_model(request):
    views_calls["/check_list_model"] += 1
    return [User(1, "John", "Password")]


@router.get("/check_model_alias", response=UserModel, by_alias=True)
@cache_page()
def check_model_alias(request):
    views_calls["/check_model_alias"] += 1
    return User(1, "John", "Password")


@router.get("/check_union", response=Union[int, UserModel])
@cache_page()
def check_union(request, q: int):
    views_calls[f"/check_union?q={q}"] += 1
    if q == 0:
        return 1
    if q == 1:
        return User(1, "John", "Password")
    return "invalid"


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
def test_responses_cache(path, expected_response):
    for _ in range(2):
        response = client.get(path)
        assert response.status_code == 200, response.content
        assert response.json() == expected_response
        assert views_calls[path] == 1


def test_check_cache_key():
    assert views_calls["custom_cache_key"] == 0
    for _ in range(2):
        response = client.get("/check_int_cache_key")
        assert response.status_code == 200, response.content
        assert response.json() == 1
        assert views_calls["custom_cache_key"] == 1


class HttpResponse(HttpResponseBase):
    streaming = False
    content = None


@router.get("/check_http")
@cache_page()
def check_http(request):
    views_calls["/check_http"] += 1
    return HttpResponse(status=204)


def test_check_http():
    assert views_calls["/check_http"] == 0
    for i in range(2):
        response = client.get("/check_http")
        assert response.status_code == 204, response.content
        assert views_calls["/check_http"] == i + 1


@router.post("/check_post")
@cache_page()
def check_post(request):
    views_calls["/check_post"] += 1
    return HttpResponse(status=200)


def test_check_post():
    assert views_calls["/check_post"] == 0
    for i in range(2):
        response = client.post("/check_post")
        assert response.status_code == 200, response.content
        assert views_calls["/check_post"] == i + 1


@router.get("/check_dict_in_cache")
@cache_page()
def check_dict_in_cache(request):
    views_calls["/check_dict_in_cache"] += 1
    key = learn_cache_key(request, HttpResponse(status=200), 3600, None, cache=cache)
    cache.set(
        key,
        {
            "content": '{"test": 2}',
            "headers": {"Content-Type": "application/json; charset=utf-8"},
        },
    )
    response = HttpResponseDjango(b'{"test": 1}', status=400)
    response["Content-Type"] = "application/json; charset=utf-8"
    return response


def test_check_dict_in_cache():
    assert views_calls["/check_dict_in_cache"] == 0
    for i in range(2):
        response = client.get("/check_dict_in_cache")
        assert response.status_code == i and 200 or 400, response.content
        assert response.json() == {"test": i + 1}, response.content
        assert views_calls["/check_dict_in_cache"] == 1


def test_cache_whithout_operation():
    val = "no_cache"
    func = cache_page()(lambda x: val)
    request = client._build_request("GET", "/", {}, {})
    assert func(request) == val
