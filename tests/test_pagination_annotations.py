from typing import List, Optional

from ninja import FilterSchema, NinjaAPI, Query, Schema
from ninja.pagination import paginate
from ninja.testing import TestClient


class ItemSchema(Schema):
    name: str


class ItemFilterSchema(FilterSchema):
    name: Optional[str] = None


def test_paginated_route_resolves_deferred_query_schema():
    api = NinjaAPI(urls_namespace="pagination_annotations")

    @api.get("/items", response=List[ItemSchema])
    @paginate
    def list_items(request, filters: "ItemFilterSchema" = Query(...)):
        return []

    response = TestClient(api).get("/items?name=example")

    assert response.status_code == 200, response.content
    assert response.json() == {"items": [], "count": 0}
