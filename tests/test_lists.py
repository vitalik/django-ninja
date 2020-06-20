import pytest
from typing import List
from ninja import Router, Query, Form
from pydantic import BaseModel
from client import NinjaClient


from django.http import QueryDict  # noqa

router = Router()


@router.post("/list1")
def listview1(
    request, query: List[int] = Query(...), form: List[int] = Form(...),
):
    return {
        "query": query,
        "form": form,
    }


@router.post("/list2")
def listview2(
    request, body: List[int], query: List[int] = Query(...),
):
    return {
        "query": query,
        "body": body,
    }


class BodyModel(BaseModel):
    x: int
    y: int


@router.post("/list3")
def listview3(request, body: List[BodyModel]):
    return {
        "body": body,
    }


@router.post("/list-default")
def listviewdefault(request, body: List[int] = [1]):
    # By default List[anything] is treated for body
    return {
        "body": body,
    }


client = NinjaClient(router)


@pytest.mark.parametrize(
    # fmt: off
    "path,kwargs,expected_response",
    [
        (
            "/list1?query=1&query=2",
            dict(data=QueryDict("form=3&form=4")),
            {"query": [1, 2], "form": [3, 4]},
        ),
        (
            "/list2?query=1&query=2",
            dict(json=[5, 6]),
            {"query": [1, 2], "body": [5, 6]},
        ),
        (
            "/list3",
            dict(json=[{"x": 1, "y": 1}]),
            {"body": [{"x": 1, "y": 1}]},
        ),
        (
            "/list-default",
            {},
            {"body": [1]},
        ),
        (
            "/list-default",
            dict(json=[1, 2]),
            {"body": [1, 2]},
        ),
    ]
    # fmt: on
)
def test_list(path, kwargs, expected_response):
    response = client.post(path, **kwargs)
    assert response.status_code == 200, response.content
    assert response.json() == expected_response
