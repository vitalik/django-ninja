from typing import Any, List

import pytest

from ninja import NinjaAPI, Schema
from ninja.errors import ConfigError
from ninja.pagination import PageNumberPagination, PaginationBase, paginate
from ninja.testing import TestClient

api = NinjaAPI()


ITEMS = list(range(100))


class CustomPagination(PaginationBase):
    # only offset param, defaults to 5 per page
    class Input(Schema):
        skip: int

    class Output(Schema):
        items: List[Any]
        count: str
        skip: int

    def paginate_queryset(self, items, pagination: Input, **params):
        skip = pagination.skip
        return {
            "items": items[skip : skip + 5],
            "count": "many",
            "skip": skip,
        }


class NoOutputPagination(PaginationBase):
    # only offset param, defaults to 5 per page but without Output schema
    class Input(Schema):
        skip: int

    Output = None

    def paginate_queryset(self, items, pagination: Input, **params):
        skip = pagination.skip
        return items[skip : skip + 5]


class ResultsPaginator(PaginationBase):
    "Use 'results' insted of 'items' for the output"

    class Input(Schema):
        skip: int

    class Output(Schema):
        results: List[int]
        count: int
        skip: int

    items_attribute: str = "results"

    def paginate_queryset(self, items, pagination: Input, **params):
        skip = pagination.skip
        return {
            "results": items[skip : skip + 5],
            "count": self._items_count(items),
            "skip": skip,
        }


@api.get("/items_1", response=List[int])
@paginate  # WITHOUT brackets (should use default pagination)
def items_1(request, **kwargs):
    return ITEMS


@api.get("/items_2", response=List[int])
@paginate()  # with brackets (should use default pagination)
def items_2(request, someparam: int = 0, **kwargs):
    # also having custom param `someparam` - that should not be lost
    return ITEMS


@api.get("/items_3", response=List[int])
@paginate(CustomPagination)
def items_3(request, **kwargs):
    return ITEMS


@api.get("/items_4", response=List[int])
@paginate(PageNumberPagination, page_size=10)
def items_4(request, **kwargs):
    return ITEMS


@api.get("/items_5", response=List[int])
@paginate(PageNumberPagination, page_size=10)
def items_5(request):
    return ITEMS


@api.get("/items_6", response={101: int, 200: List[Any]})
@paginate(PageNumberPagination, page_size=10, pass_parameter="page_info")
def items_6(request, **kwargs):
    return ITEMS + [kwargs["page_info"]]


@api.get("/items_7", response=List[int])
@paginate(NoOutputPagination)
def items_7(request):
    return [7] * 7


@api.get("/items_8", response=List[int])
@paginate(ResultsPaginator)
def items_8(request):
    return list(range(1000))


client = TestClient(api)


def test_case1():
    response = client.get("/items_1?limit=10").json()
    assert response == {"items": ITEMS[:10], "count": 100}

    schema = api.get_openapi_schema()["paths"]["/api/items_1"]["get"]
    # print(schema)
    assert schema["parameters"] == [
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


def test_case2():
    response = client.get("/items_2?limit=10").json()
    assert response == {"items": ITEMS[:10], "count": 100}

    schema = api.get_openapi_schema()["paths"]["/api/items_2"]["get"]
    print(schema["parameters"])
    assert schema["parameters"] == [
        {
            "in": "query",
            "name": "someparam",
            "schema": {"title": "Someparam", "default": 0, "type": "integer"},
            "required": False,
        },
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


def test_case3():
    response = client.get("/items_3?skip=5").json()
    assert response == {"items": ITEMS[5:10], "count": "many", "skip": 5}

    schema = api.get_openapi_schema()["paths"]["/api/items_3"]["get"]
    print(schema)
    assert schema["parameters"] == [
        {
            "in": "query",
            "name": "skip",
            "schema": {"title": "Skip", "type": "integer"},
            "required": True,
        }
    ]


def test_case4():
    response = client.get("/items_4?page=2").json()
    assert response == {"items": ITEMS[10:20], "count": 100}

    schema = api.get_openapi_schema()["paths"]["/api/items_4"]["get"]
    # print(schema)
    assert schema["parameters"] == [
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
        }
    ]


def test_case5_no_kwargs():
    response = client.get("/items_5?page=2").json()
    assert response == {"items": ITEMS[10:20], "count": 100}

    schema = api.get_openapi_schema()["paths"]["/api/items_5"]["get"]

    assert schema["parameters"] == [
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
        }
    ]


def test_case6_pass_param_kwargs():
    page = 11
    response = client.get(f"/items_6?page={page}").json()
    assert response == {"items": [{"page": 11}], "count": 101}

    schema = api.get_openapi_schema()["paths"]["/api/items_6"]["get"]

    assert schema["parameters"] == [
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
        }
    ]


def test_case7():
    response = client.get("/items_7?skip=5").json()
    assert response == [7, 7]

    schema = api.get_openapi_schema()["paths"]["/api/items_7"]["get"]
    response = schema["responses"][200]["content"]["application/json"]["schema"]

    assert response == {
        "title": "Response",
        "type": "array",
        "items": {"type": "integer"},
    }


def test_case8():
    response = client.get("/items_8?skip=5").json()
    assert response == {"results": [5, 6, 7, 8, 9], "count": 1000, "skip": 5}


def test_config_error_None():
    with pytest.raises(ConfigError):

        @api.get("/invalid1", response={200: None})
        @paginate
        def invalid1(request):
            pass


def test_config_error_NOT_SET():
    with pytest.raises(ConfigError):

        @api.get("/invalid2")
        @paginate
        def invalid2(request):
            pass
