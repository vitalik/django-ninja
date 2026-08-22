from sys import version_info
from typing import List

import pytest
from django.http import HttpRequest

from ninja import NinjaAPI, Query, Schema
from ninja.pagination import PageNumberPagination, paginate
from ninja.testing import TestClient

pytestmark = pytest.mark.skipif(
    version_info < (3, 14),
    reason="requires Python 3.14 deferred annotations",
)


class DeferredQuerySchema(Schema):
    foo: str


class AuthenticatedNinjaRequest(HttpRequest):
    auth: str


if version_info >= (3, 14):

    class ResolveWithSelfReference(Schema):
        name: str

        @staticmethod
        def resolve_name(obj) -> ResolveWithSelfReference:  # noqa: F821
            return obj.get("name", "default")

else:
    ResolveWithSelfReference = None


def test_paginated_route_with_deferred_annotations():
    api = NinjaAPI(urls_namespace="annotations_py314")

    @api.get("/endpoint", response=List[int])
    @paginate(PageNumberPagination)
    def endpoint(
        request: AuthenticatedNinjaRequest,
        params: Query[DeferredQuerySchema],
    ):
        return []

    client = TestClient(api)
    response = client.get("/endpoint?foo=test")

    assert response.status_code == 200, response.content
    assert response.json() == {"items": [], "count": 0}


def test_schema_with_self_referencing_resolver_annotation():
    assert ResolveWithSelfReference is not None
    obj = ResolveWithSelfReference.model_validate({"name": "test"})
    assert obj.name == "test"
