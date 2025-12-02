from typing import List

import pytest

from ninja import NinjaAPI, Schema
from ninja.pagination import PageNumberPagination, RouterPaginated, paginate
from ninja.testing import TestAsyncClient, TestClient

api = NinjaAPI(default_router=RouterPaginated())


class ItemSchema(Schema):
    id: int


@api.get("/items", response=List[ItemSchema])
def items(request):
    return [{"id": i} for i in range(1, 51)]


@api.get("/items_nolist", response=ItemSchema)
def items_nolist(request):
    return {"id": 1}


@api.get("/items_extra_layer", response=List[ItemSchema])
@paginate  # has not to break down
def items_extra_layer(request):
    return [{"id": i} for i in range(1, 51)]


@api.get("/items_overridden", response=List[ItemSchema])
@paginate(PageNumberPagination, page_size=3)  # has precedence over router pagination
def items_overridden_pagination(request):
    return [{"id": i} for i in range(1, 51)]


client = TestClient(api)


def test_for_list_reponse():
    parameters = api.get_openapi_schema()["paths"]["/api/items"]["get"]["parameters"]
    assert parameters == [
        {
            "in": "query",
            "name": "limit",
            "schema": {
                "title": "Limit",
                "default": 100,
                "minimum": 1,
                "type": "integer",
            },
            "required": False,
        },
        {
            "in": "query",
            "name": "offset",
            "schema": {
                "title": "Offset",
                "default": 0,
                "minimum": 0,
                "type": "integer",
            },
            "required": False,
        },
    ]

    response = client.get("/items?offset=5&limit=1").json()
    # print(response)
    assert response == {"items": [{"id": 6}], "count": 50}


def test_for_NON_list_reponse():
    parameters = api.get_openapi_schema()["paths"]["/api/items_nolist"]["get"][
        "parameters"
    ]
    # print(parameters)
    assert parameters == []


def test_extra_pagination_layer_does_not_crash():
    parameters = api.get_openapi_schema()["paths"]["/api/items_extra_layer"]["get"][
        "parameters"
    ]
    assert parameters == [
        {
            "in": "query",
            "name": "limit",
            "schema": {
                "title": "Limit",
                "default": 100,
                "minimum": 1,
                "type": "integer",
            },
            "required": False,
        },
        {
            "in": "query",
            "name": "offset",
            "schema": {
                "title": "Offset",
                "default": 0,
                "minimum": 0,
                "type": "integer",
            },
            "required": False,
        },
    ]

    response = client.get("/items_extra_layer?offset=5&limit=1").json()
    assert response == {"items": [{"id": 6}], "count": 50}


def test_for_list_with_overridden_pagination_reponse():
    parameters = api.get_openapi_schema()["paths"]["/api/items_overridden"]["get"][
        "parameters"
    ]
    assert parameters == [
        {
            "in": "query",
            "name": "page",
            "schema": {
                "title": "Page",
                "default": 1,
                "minimum": 1,
                "type": "integer",
            },
            "required": False,
        },
        {
            "in": "query",
            "name": "page_size",
            "schema": {
                "anyOf": [{"minimum": 1, "type": "integer"}, {"type": "null"}],
                "title": "Page Size",
            },
            "required": False,
        },
    ]

    response = client.get("/items_overridden?page=5").json()
    assert response == {"items": [{"id": 13}, {"id": 14}, {"id": 15}], "count": 50}


@pytest.mark.asyncio
async def test_async_pagination():
    @api.get("/items_async", response=List[ItemSchema])
    async def items_async(request):
        return [{"id": i} for i in range(1, 51)]

    client = TestAsyncClient(api)

    response = await client.get("/items_async?offset=5&limit=1")
    assert response.json() == {"items": [{"id": 6}], "count": 50}
