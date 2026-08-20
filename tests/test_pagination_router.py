from typing import Annotated, List, TypeVar

import pytest
from typing_extensions import TypeAliasType

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


# PEP 695 `type` aliases used as response types. Each is a regression test for
# the pagination element extraction: a bare alias (`type X = List[Book]`), an
# alias whose value is `Annotated[List[Book], ...]`, and a parameterized
# generic alias (`type X[T] = List[T]; X[Book]`). Without the shared
# get_collection_item helper, _find_collection_response would raise IndexError
# for the bare and Annotated shapes (get_args is empty on a bare alias and
# returns the wrapper for Annotated) and would lose the typevar for the
# parameterized generic. TypeAliasType(...) is used so the file imports on
# Python < 3.12.

ItemListAlias = TypeAliasType("ItemListAlias", List[ItemSchema])
ItemListAnnotatedAlias = TypeAliasType(
    "ItemListAnnotatedAlias", Annotated[List[ItemSchema], "meta"]
)
_T = TypeVar("_T")
ItemListGenericAlias = TypeAliasType(
    "ItemListGenericAlias", List[_T], type_params=(_T,)
)


@api.get("/items_alias", response=ItemListAlias)
def items_alias(request):
    return [{"id": i} for i in range(1, 4)]


@api.get("/items_annotated_alias", response=ItemListAnnotatedAlias)
def items_annotated_alias(request):
    return [{"id": i} for i in range(1, 4)]


@api.get("/items_generic_alias", response=ItemListGenericAlias[ItemSchema])
def items_generic_alias(request):
    return [{"id": i} for i in range(1, 4)]


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
    # Create separate API for async test to avoid frozen router issues
    async_api = NinjaAPI(default_router=RouterPaginated(), urls_namespace="async_test")

    @async_api.get("/items_async", response=List[ItemSchema])
    async def items_async(request):
        return [{"id": i} for i in range(1, 51)]

    client = TestAsyncClient(async_api)

    response = await client.get("/items_async?offset=5&limit=1")
    assert response.json() == {"items": [{"id": 6}], "count": 50}


# ---------------------------------------------------------------------------
# Pagination with PEP 695 `type` aliases as response types.
# Each test asserts both the paginated body shape and the OpenAPI response
# schema so that an unresolved TypeVar or a nested-list item schema is caught
# (a bare 200 check would miss both).
# ---------------------------------------------------------------------------


def _paged_items_ref(path: str) -> dict:
    """Return the OpenAPI response component schema for a paginated
    ``List[ItemSchema]`` endpoint at ``path``. The response is a ``$ref`` to a
    ``PagedItemSchema`` component whose ``items`` array element is
    ``$ref ItemSchema``."""
    schema = api.get_openapi_schema()
    response_schema = schema["paths"][path]["get"]["responses"][200]["content"][
        "application/json"
    ]["schema"]
    # The response schema is a $ref; resolve it to the component definition.
    assert "$ref" in response_schema, response_schema
    ref = response_schema["$ref"]
    component_name = ref.rsplit("/", 1)[-1]
    return schema["components"]["schemas"][component_name]


def _assert_paged_item_schema(component: dict) -> None:
    """Assert a Paged* component has an ``items`` array of ItemSchema and a
    ``count`` integer (the standard pagination shape). Catches an unresolved
    TypeVar (which would produce a broken or missing ``items`` element ref)
    and a nested-list item (which would point to a ``Paged*`` of ``List``)."""
    assert component["type"] == "object"
    assert component["required"] == ["items", "count"]
    items = component["properties"]["items"]
    assert items["type"] == "array"
    assert items["items"] == {"$ref": "#/components/schemas/ItemSchema"}
    assert component["properties"]["count"]["type"] == "integer"


def test_paginated_response_via_bare_type_alias():
    """``response=ItemListAlias`` where ``type ItemListAlias = List[ItemSchema]``
    paginates correctly and the OpenAPI item schema points to ItemSchema."""
    response = client.get("/items_alias?limit=2")
    assert response.status_code == 200, response.json()
    assert response.json() == {"items": [{"id": 1}, {"id": 2}], "count": 3}

    _assert_paged_item_schema(_paged_items_ref("/api/items_alias"))


def test_paginated_response_via_annotated_type_alias():
    """``response=ItemListAnnotatedAlias`` where the alias value is
    ``Annotated[List[ItemSchema], ...]`` paginates correctly (the Annotated
    wrapper is peeled before element extraction, so the item schema is
    ItemSchema, not ``List[ItemSchema]``)."""
    response = client.get("/items_annotated_alias?limit=2")
    assert response.status_code == 200, response.json()
    assert response.json() == {"items": [{"id": 1}, {"id": 2}], "count": 3}

    _assert_paged_item_schema(_paged_items_ref("/api/items_annotated_alias"))


def test_paginated_response_via_parameterized_generic_type_alias():
    """``response=ItemListGenericAlias[ItemSchema]`` where
    ``type ItemListGenericAlias[T] = List[T]`` paginates correctly and the
    TypeVar ``T`` is resolved to ``ItemSchema`` (a bare 200 check would miss
    an unresolved TypeVar that produces a broken OpenAPI schema)."""
    response = client.get("/items_generic_alias?limit=2")
    assert response.status_code == 200, response.json()
    assert response.json() == {"items": [{"id": 1}, {"id": 2}], "count": 3}

    _assert_paged_item_schema(_paged_items_ref("/api/items_generic_alias"))


def test_find_collection_response_raises_on_collection_without_element():
    """``_find_collection_response`` raises ``ConfigError`` when a response is
    recognized as a collection by ``is_collection_type`` but
    ``get_collection_item`` cannot extract an element type (e.g. a bare
    ``type X = list`` alias with no type argument). This covers the defensive
    fallthrough path added alongside the alias-aware extraction."""
    from ninja.errors import ConfigError
    from ninja.operation import Operation
    from ninja.pagination import _find_collection_response

    BareListNoArgAlias = TypeAliasType("BareListNoArgAlias", list)

    def view_func(request):
        return []

    op = Operation("/whatever", ["GET"], view_func, response=BareListNoArgAlias)
    with pytest.raises(ConfigError):
        _find_collection_response(op)
