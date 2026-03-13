from typing import List, Union
from unittest.mock import patch

import pytest

from ninja import Field, NinjaAPI, Schema, Status
from ninja.operation import ResponseObject
from ninja.pagination import LimitOffsetPagination, paginate
from ninja.responses import codes_2xx, codes_3xx
from ninja.testing import TestAsyncClient, TestClient

# -- Schemas --


class UserOut(Schema):
    id: int
    name: str


class UserOutSub(UserOut):
    extra: str = "default"


class ErrorOut(Schema):
    detail: str


class AliasOut(Schema):
    user_name: str = Field(serialization_alias="userName")


# -- API for basic Status tests --

api = NinjaAPI()


@api.get("/status_dict", response={200: UserOut, 400: ErrorOut})
def status_dict(request):
    return Status(200, {"id": 1, "name": "John"})


@api.get("/status_error", response={200: UserOut, 400: ErrorOut})
def status_error(request):
    return Status(400, {"detail": "bad request"})


@api.get("/status_none", response={204: None})
def status_none(request):
    return Status(204, None)


@api.get("/status_ellipsis", response={200: UserOut, ...: ErrorOut})
def status_ellipsis(request, code: int):
    if code == 200:
        return Status(200, {"id": 1, "name": "John"})
    return Status(code, {"detail": "fallback"})


@api.get("/status_code_groups", response={codes_2xx: UserOut, codes_3xx: ErrorOut})
def status_code_groups(request, code: int):
    if code < 300:
        return Status(code, {"id": 1, "name": "John"})
    return Status(code, {"detail": "redirect"})


@api.get("/status_model_instance", response={200: UserOut})
def status_model_instance(request):
    return Status(200, UserOut(id=1, name="John"))


# -- Tuple deprecation --


@api.get("/tuple_return", response={200: UserOut, 400: ErrorOut})
def tuple_return(request):
    return 200, {"id": 1, "name": "John"}


# -- Skip re-validation --


@api.get("/model_instance", response=UserOut)
def model_instance(request):
    return UserOut(id=1, name="John")


@api.get("/model_subclass", response=UserOut)
def model_subclass(request):
    return UserOutSub(id=1, name="John", extra="bonus")


@api.get("/dict_result", response=UserOut)
def dict_result(request):
    return {"id": 1, "name": "John"}


@api.get("/union_response", response={200: Union[int, UserOut], 400: ErrorOut})
def union_response(request, q: int):
    if q == 0:
        return Status(200, 1)
    return Status(200, UserOut(id=1, name="John"))


@api.get("/list_response", response={200: List[UserOut]})
def list_response(request):
    return Status(200, [{"id": 1, "name": "John"}])


@api.get("/by_alias_response", response=AliasOut, by_alias=True)
def by_alias_response(request):
    return AliasOut(user_name="Alice")


# -- Pagination + Status --


@api.get("/paginated_status", response={201: List[UserOut]})
@paginate(LimitOffsetPagination)
def paginated_status(request):
    return Status(
        201,
        [{"id": 1, "name": "A"}, {"id": 2, "name": "B"}, {"id": 3, "name": "C"}],
    )


@api.get("/paginated_normal", response=List[UserOut])
@paginate(LimitOffsetPagination)
def paginated_normal(request):
    return [{"id": 1, "name": "A"}, {"id": 2, "name": "B"}]


# Async pagination
async_api = NinjaAPI()


@async_api.get("/async_paginated_status", response={201: List[UserOut]})
@paginate(LimitOffsetPagination)
async def async_paginated_status(request):
    return Status(
        201,
        [{"id": 1, "name": "A"}, {"id": 2, "name": "B"}, {"id": 3, "name": "C"}],
    )


@async_api.get("/async_paginated_normal", response=List[UserOut])
@paginate(LimitOffsetPagination)
async def async_paginated_normal(request):
    return [{"id": 1, "name": "A"}, {"id": 2, "name": "B"}]


# -- Clients --

client = TestClient(api)
async_client = TestAsyncClient(async_api)


# -- Tests: Status basic --


class TestStatusGeneric:
    def test_subscriptable_at_runtime(self):
        """Status[dict] should not raise TypeError (GitHub #1693)."""
        alias = Status[dict]
        assert alias is not None


class TestStatusBasic:
    def test_status_with_dict(self):
        response = client.get("/status_dict")
        assert response.status_code == 200
        assert response.json() == {"id": 1, "name": "John"}

    def test_status_error_code(self):
        response = client.get("/status_error")
        assert response.status_code == 400
        assert response.json() == {"detail": "bad request"}

    def test_status_none_204(self):
        response = client.get("/status_none")
        assert response.status_code == 204
        assert response.content == b""

    def test_status_ellipsis_200(self):
        response = client.get("/status_ellipsis?code=200")
        assert response.status_code == 200
        assert response.json() == {"id": 1, "name": "John"}

    def test_status_ellipsis_fallback(self):
        response = client.get("/status_ellipsis?code=500")
        assert response.status_code == 500
        assert response.json() == {"detail": "fallback"}

    def test_status_code_groups_2xx(self):
        response = client.get("/status_code_groups?code=200")
        assert response.status_code == 200
        assert response.json() == {"id": 1, "name": "John"}

    def test_status_code_groups_201(self):
        response = client.get("/status_code_groups?code=201")
        assert response.status_code == 201
        assert response.json() == {"id": 1, "name": "John"}

    def test_status_code_groups_3xx(self):
        response = client.get("/status_code_groups?code=300")
        assert response.status_code == 300
        assert response.json() == {"detail": "redirect"}

    def test_status_wrapping_model_instance(self):
        response = client.get("/status_model_instance")
        assert response.status_code == 200
        assert response.json() == {"id": 1, "name": "John"}


# -- Tests: Tuple deprecation --


class TestTupleDeprecation:
    def test_tuple_emits_deprecation_warning(self):
        with pytest.warns(DeprecationWarning, match="deprecated.*Status"):
            client.get("/tuple_return")


# -- Tests: Skip re-validation --


class TestSkipRevalidation:
    def test_model_instance_skips_validation(self):
        with patch(
            "ninja.operation.ResponseObject", wraps=ResponseObject
        ) as mock_resp_obj:
            response = client.get("/model_instance")
            assert response.status_code == 200
            assert response.json() == {"id": 1, "name": "John"}
            mock_resp_obj.assert_not_called()

    def test_subclass_skips_validation(self):
        with patch(
            "ninja.operation.ResponseObject", wraps=ResponseObject
        ) as mock_resp_obj:
            response = client.get("/model_subclass")
            assert response.status_code == 200
            assert response.json() == {"id": 1, "name": "John", "extra": "bonus"}
            mock_resp_obj.assert_not_called()

    def test_dict_goes_through_validation(self):
        with patch(
            "ninja.operation.ResponseObject", wraps=ResponseObject
        ) as mock_resp_obj:
            response = client.get("/dict_result")
            assert response.status_code == 200
            assert response.json() == {"id": 1, "name": "John"}
            mock_resp_obj.assert_called_once()

    def test_union_no_skip(self):
        # Union types should still go through full validation
        with patch(
            "ninja.operation.ResponseObject", wraps=ResponseObject
        ) as mock_resp_obj:
            response = client.get("/union_response?q=1")
            assert response.status_code == 200
            assert response.json() == {"id": 1, "name": "John"}
            mock_resp_obj.assert_called_once()

    def test_list_no_skip(self):
        # List types should still go through full validation
        with patch(
            "ninja.operation.ResponseObject", wraps=ResponseObject
        ) as mock_resp_obj:
            response = client.get("/list_response")
            assert response.status_code == 200
            assert response.json() == [{"id": 1, "name": "John"}]
            mock_resp_obj.assert_called_once()

    def test_by_alias_serialization(self):
        response = client.get("/by_alias_response")
        assert response.status_code == 200
        assert response.json() == {"userName": "Alice"}

    def test_status_wrapping_model_skips_validation(self):
        with patch(
            "ninja.operation.ResponseObject", wraps=ResponseObject
        ) as mock_resp_obj:
            response = client.get("/status_model_instance")
            assert response.status_code == 200
            assert response.json() == {"id": 1, "name": "John"}
            mock_resp_obj.assert_not_called()


# -- Tests: Pagination + Status --


class TestPaginationStatus:
    def test_sync_pagination_with_status(self):
        response = client.get("/paginated_status?limit=2&offset=0")
        assert response.status_code == 201
        data = response.json()
        assert data["count"] == 3
        assert len(data["items"]) == 2
        assert data["items"][0] == {"id": 1, "name": "A"}

    def test_sync_pagination_without_status(self):
        response = client.get("/paginated_normal?limit=2&offset=0")
        assert response.status_code == 200
        data = response.json()
        assert data["count"] == 2
        assert len(data["items"]) == 2

    @pytest.mark.asyncio
    async def test_async_pagination_with_status(self):
        response = await async_client.get("/async_paginated_status?limit=2&offset=0")
        assert response.status_code == 201
        data = response.json()
        assert data["count"] == 3
        assert len(data["items"]) == 2
        assert data["items"][0] == {"id": 1, "name": "A"}

    @pytest.mark.asyncio
    async def test_async_pagination_without_status(self):
        response = await async_client.get("/async_paginated_normal?limit=2&offset=0")
        assert response.status_code == 200
        data = response.json()
        assert data["count"] == 2
        assert len(data["items"]) == 2
