from typing import List

import pytest

from ninja import NinjaAPI, Schema
from ninja.pagination import paginate
from ninja.testing import TestAsyncClient

from someapp.models import Event

api = NinjaAPI()


class DummySchema(Schema):
    id: int
    name: str


@api.get("/async_view_return_queryset/", response=List[DummySchema])
@paginate
async def async_view_return_queryset(request, **kwargs) -> None:
    return Event.objects.all()


@api.get("/async_view_return_list/", response=List[DummySchema])
@paginate
async def async_view_return_list(request, **kwargs) -> None:
    return []


@pytest.mark.asyncio
@pytest.mark.django_db
async def test_success__async_paginated_async_view_return_queryset() -> None:
    client = TestAsyncClient(api)
    await client.get("/async_view_return_queryset/")  # not raising any exception


@pytest.mark.asyncio
@pytest.mark.django_db
async def test_success__async_paginated_async_view_return_list() -> None:
    client = TestAsyncClient(api)
    await client.get("/async_view_return_list/")  # not raising any exception
