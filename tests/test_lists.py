from typing import List

import pytest
from django.http import QueryDict  # noqa
from pydantic import BaseModel, Field, conlist

from ninja import Form, Query, Router, Schema
from ninja.testing import TestClient

router = Router()


@router.post("/list1")
def listview1(
    request,
    query: List[int] = Query(...),
    form: List[int] = Form(...),
):
    return {
        "query": query,
        "form": form,
    }


@router.post("/list2")
def listview2(
    request,
    body: List[int],
    query: List[int] = Query(...),
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


class Filters(Schema):
    tags: List[str] = []
    other_tags: List[str] = Field([], alias="other_tags_alias")


@router.post("/list4")
def listview4(
    request,
    filters: Filters = Query(...),
):
    return {
        "filters": filters,
    }


class ConListSchema(Schema):
    query: conlist(int, min_items=1)


class Data(Schema):
    data: ConListSchema


@router.post("/list5")
def listview5(
    request,
    body: conlist(int, min_items=1),
    a_query: Data = Query(...),
):
    return {
        "query": a_query.data.query,
        "body": body,
    }


@router.post("/list6")
def listview6(
    request,
    object_id: List[int] = Query(None, alias="id"),
):
    return {"query": object_id}


client = TestClient(router)


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
        (
            "/list4?tags=a&tags=b&other_tags_alias=a&other_tags_alias=b",
            {},
            {"filters": {"tags": ["a", "b"], "other_tags": ["a", "b"]}},
        ),
        (
            "/list4?tags=abc&other_tags_alias=abc",
            {},
            {"filters": {"tags": ["abc"], "other_tags": ["abc"]}},
        ),
        (
            "/list4",
            {},
            {"filters": {"tags": [], "other_tags": []}},
        ),
        (
            "/list5?query=1&query=2",
            dict(json=[5, 6]),
            {"query": [1, 2], "body": [5, 6]},
        ),
        (
            "/list6?id=1&id=2",
            {},
            {"query": [1, 2]},
        ),
    ]
    # fmt: on
)
def test_list(path, kwargs, expected_response):
    response = client.post(path, **kwargs)
    assert response.status_code == 200, response.content
    assert response.json() == expected_response
