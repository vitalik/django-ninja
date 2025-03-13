import importlib
from sys import version_info
from typing import Any, List

import pytest
from django.test import override_settings
from pydantic.errors import PydanticSchemaGenerationError

from ninja import NinjaAPI, Schema
from ninja.errors import ConfigError
from ninja.operation import Operation
from ninja.pagination import (
    LimitOffsetPagination,
    PageNumberPagination,
    PaginationBase,
    make_response_paginated,
    paginate,
)
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
    # Outputs items without count attribute
    class Input(Schema):
        skip: int

    Output = None

    def paginate_queryset(self, items, pagination: Input, **params):
        skip = pagination.skip
        return items[skip : skip + 5]


class ResultsPaginator(PaginationBase):
    "Use 'results' instead of 'items' for the output"

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


class NextPrevPagination(PaginationBase):
    # only offset param, defaults to 5 per page
    class Input(Schema):
        skip: int

    class Output(Schema):
        items: List[Any]
        next: str = None
        prev: str = None

    def paginate_queryset(self, items, pagination: Input, request, **params):
        skip = pagination.skip
        prev_skip = skip - 5
        if prev_skip < 0:
            prev_skip = 0
        return {
            "items": items[skip : skip + 5],
            "next": request.build_absolute_uri(f"?skip={skip + 5}"),
            "prev": request.build_absolute_uri(f"?skip={prev_skip}"),
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
    return list(range(15))


@api.get("/items_8", response=List[int])
@paginate(ResultsPaginator)
def items_8(request):
    return list(range(1000))


@api.get("/items_9", response=List[int])
@paginate(NextPrevPagination)
def items_9(request):
    return list(range(100))


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
    # print(schema["parameters"])
    assert schema["parameters"] == [
        {
            "in": "query",
            "name": "someparam",
            "schema": {"default": 0, "title": "Someparam", "type": "integer"},
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
    # print(schema)
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
    response = client.get("/items_7?skip=10").json()
    assert response == [10, 11, 12, 13, 14]

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


def test_case9():
    response = client.get("/items_9?skip=5").json()
    assert response == {
        "items": [5, 6, 7, 8, 9],
        "next": "http://testlocation/?skip=10",
        "prev": "http://testlocation/?skip=0",
    }


@override_settings(NINJA_PAGINATION_MAX_LIMIT=1000)
def test_10_max_limit_set():
    # reload to apply django settings
    from ninja import conf, pagination

    importlib.reload(conf)
    importlib.reload(pagination)
    new_api = NinjaAPI()
    new_client = TestClient(new_api)

    @new_api.get("/items_10", response=List[int])
    @paginate  # LimitOffsetPagination is set as default
    def items_10(request, **kwargs):
        return ITEMS

    response = new_client.get("/items_10?limit=1000").json()
    assert response == {"items": ITEMS[:1000], "count": 100}

    schema = new_api.get_openapi_schema()["paths"]["/api/items_10"]["get"]
    # print(schema)
    assert schema["parameters"] == [
        {
            "in": "query",
            "name": "limit",
            "schema": {
                "title": "Limit",
                "default": 100,
                "minimum": 1,
                "maximum": 1000,
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


@override_settings(NINJA_PAGINATION_MAX_LIMIT=1000)
def test_11_max_limit_set_and_exceeded():
    # reload to apply django settings
    from ninja import conf, pagination

    importlib.reload(conf)
    importlib.reload(pagination)
    new_api = NinjaAPI()
    new_client = TestClient(new_api)

    @new_api.get("/items_11", response=List[int])
    @paginate  # LimitOffsetPagination is set as default
    def items_11(request, **kwargs):
        return ITEMS

    response = new_client.get("/items_11?limit=1001").json()
    assert response == {
        "detail": [
            {
                "ctx": {"le": 1000},
                "loc": ["query", "limit"],
                "msg": "Input should be less than or equal to 1000",
                "type": "less_than_equal",
            }
        ]
    }


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


@pytest.mark.skipif(version_info < (3, 11), reason="Not needed at this Python version")
def test_pagination_works_with_unnamed_classes():
    """
    This test lets you check that the typing.Any case handled in `ninja.pagination.make_response_paginated`
    works for Python>=3.11, as a typing.Any does possess the __name__ attribute past that version
    """
    operation = Operation("/whatever", ["GET"], lambda: None, response=List[int])
    operation.response_models[200].__annotations__["response"] = List[object()]
    with pytest.raises(
        PydanticSchemaGenerationError
    ):  # It does fail after we passed the logic that we are testing
        make_response_paginated(LimitOffsetPagination, operation)
