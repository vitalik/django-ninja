from unittest import mock

import pytest
from pydantic import model_serializer

from ninja import Router, Schema
from ninja.schema import pydantic_version
from ninja.testing import TestClient


def api_endpoint_test(request):
    return {
        "test1": "foo",
        "test2": "bar",
    }


@pytest.mark.skipif(
    pydantic_version < [2, 7],
    reason="Serialization context was introduced in Pydantic 2.7",
)
def test_request_is_passed_in_context_when_supported():
    class SchemaWithCustomSerializer(Schema):
        test1: str
        test2: str

        @model_serializer(mode="wrap")
        def ser_model(self, handler, info):
            assert "request" in info.context
            assert info.context["request"].path == "/test"  # check it is HttRequest
            assert "response_status" in info.context

            return handler(self)

    router = Router()
    router.add_api_operation(
        "/test", ["GET"], api_endpoint_test, response=SchemaWithCustomSerializer
    )

    TestClient(router).get("/test")


@pytest.mark.parametrize(
    ["pydantic_version"],
    [
        [[2, 0]],
        [[2, 4]],
        [[2, 6]],
    ],
)
def test_no_serialisation_context_used_when_no_supported(pydantic_version):
    class SchemaWithCustomSerializer(Schema):
        test1: str
        test2: str

        @model_serializer(mode="wrap")
        def ser_model(self, handler, info):
            if hasattr(info, "context"):
                # an actually newer Pydantic, but pydantic_version is still mocked, so no context is expected
                assert info.context is None

            return handler(self)

    with mock.patch("ninja.operation.pydantic_version", pydantic_version):
        router = Router()
        router.add_api_operation(
            "/test", ["GET"], api_endpoint_test, response=SchemaWithCustomSerializer
        )

        resp_json = TestClient(router).get("/test").json()

        assert resp_json == {
            "test1": "foo",
            "test2": "bar",
        }
