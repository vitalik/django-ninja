import asyncio
from typing import Any, List

import pytest
from django.db.models import QuerySet

from ninja import NinjaAPI, Schema
from ninja.errors import ConfigError
from ninja.pagination import (
    AsyncPaginationBase,
    PageNumberPagination,
    PaginationBase,
    paginate,
)
from ninja.testing import TestAsyncClient

api = NinjaAPI()

ITEMS = list(range(100))


class NoAsyncPagination(PaginationBase):
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


class AsyncNoOutputPagination(AsyncPaginationBase):
    # Outputs items without count attribute
    class Input(Schema):
        skip: int

    Output = None

    def paginate_queryset(self, items, pagination: Input, **params):
        skip = pagination.skip
        return items[skip : skip + 5]

    async def apaginate_queryset(self, items, pagination: Input, **params):
        await asyncio.sleep(0)
        skip = pagination.skip
        return items[skip : skip + 5]

    async def _items_count(self, queryset: QuerySet) -> int:
        try:
            # forcing to find queryset.count instead of list.count:
            return queryset.all().count()
        except AttributeError:
            await asyncio.sleep(0)
            return len(queryset)


@pytest.mark.asyncio
async def test_async_config_error():
    api = NinjaAPI()

    with pytest.raises(
        ConfigError, match="Pagination class not configured for async requests"
    ):

        @api.get("/items_async_undefined", response=List[int])
        @paginate(NoAsyncPagination)
        async def items_async_undefined(request, **kwargs):
            return ITEMS


@pytest.mark.asyncio
async def test_async_custom_pagination():
    api = NinjaAPI()

    @api.get("/items_async", response=List[int])
    @paginate(AsyncNoOutputPagination)
    async def items_async(request):
        return ITEMS

    client = TestAsyncClient(api)

    response = await client.get("/items_async?skip=10")
    assert response.json() == [10, 11, 12, 13, 14]


@pytest.mark.asyncio
async def test_async_default():
    api = NinjaAPI()

    @api.get("/items_default", response=List[int])
    @paginate  # WITHOUT brackets (should use default pagination)
    async def items_default(request, someparam: int = 0, **kwargs):
        await asyncio.sleep(0)
        return ITEMS

    client = TestAsyncClient(api)

    response = await client.get("/items_default?limit=10")
    assert response.json() == {"items": ITEMS[:10], "count": 100}


@pytest.mark.asyncio
async def test_async_page_number():
    api = NinjaAPI()

    @api.get("/items_page_number", response=List[Any])
    @paginate(PageNumberPagination, page_size=10, pass_parameter="page_info")
    async def items_page_number(request, **kwargs):
        return ITEMS + [kwargs["page_info"]]

    client = TestAsyncClient(api)

    response = await client.get("/items_page_number?page=11")
    assert response.json() == {"items": [{"page": 11}], "count": 101}
