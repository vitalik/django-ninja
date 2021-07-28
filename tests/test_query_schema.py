from datetime import datetime
from enum import IntEnum

import pytest
from pydantic import Field

from ninja import NinjaAPI, Query, Schema, files
from ninja.testing import TestClient
from pydantic.schema import model_schema


class Range(IntEnum):
    TWENTY = 20
    FIFTY = 50
    TWO_HUNDRED = 200


class Filter(Schema):
    to_datetime: datetime = Field(alias="to")
    from_datetime: datetime = Field(alias="from")
    range: Range = Range.TWENTY


api = NinjaAPI()


@api.get("/test")
def query_params_schema(request, filters: Filter = Query(...)):
    return filters.dict()


@api.get("/test-mixed")
def query_params_mixed_schema(
    request, query1: int, query2: int = 5, filters: Filter = Query(...)
):
    return dict(query1=query1, query2=query2, **filters.dict())


def test_request():
    client = TestClient(api)
    response = client.get("/test?from=1&to=2&range=20&foo=1&range2=50")
    print(response.json())
    assert response.json() == {
        "to_datetime": "1970-01-01T00:00:02Z",
        "from_datetime": "1970-01-01T00:00:01Z",
        "range": 20,
    }

    response = client.get("/test?from=1&to=2&range=21")
    assert response.status_code == 422


def test_request_mixed():
    client = TestClient(api)
    response = client.get("/test-mixed?from=1&to=2&range=20&foo=1&range2=50&query1=2")
    print(response.json())
    assert response.json() == {
        "to_datetime": "1970-01-01T00:00:02Z",
        "from_datetime": "1970-01-01T00:00:01Z",
        "range": 20,
        "query1": 2,
        "query2": 5,
    }

    response = client.get(
        "/test-mixed?from=1&to=2&range=20&foo=1&range2=50&query1=2&query2=10"
    )
    print(response.json())
    assert response.json() == {
        "to_datetime": "1970-01-01T00:00:02Z",
        "from_datetime": "1970-01-01T00:00:01Z",
        "range": 20,
        "query1": 2,
        "query2": 10,
    }

    response = client.get("/test-mixed?from=1&to=2")
    assert response.status_code == 422


def test_request_mixed_multiple():
    def add_with_error():
        @api.get("/test-mixed")
        def query_params_mixed_schema(
            request, filters1: Filter = Query(...), filters2: Filter = Query(...)
        ):
            pass

    with pytest.raises(
        AssertionError,
        match="Only one pydantic model allowed in query: filters1,filters2",
    ):
        add_with_error()


def test_schema():
    schema = api.get_openapi_schema()
    params = schema["paths"]["/api/test"]["get"]["parameters"]
    print(params)
    assert params == [
        {
            "in": "query",
            "name": "to",
            "schema": {"title": "To", "type": "string", "format": "date-time"},
            "required": True,
        },
        {
            "in": "query",
            "name": "from",
            "schema": {"title": "From", "type": "string", "format": "date-time"},
            "required": True,
        },
        {
            "in": "query",
            "name": "range",
            "schema": {
                "default": 20,
                "allOf": [
                    {
                        "title": "Range",
                        "description": "An enumeration.",
                        "enum": [20, 50, 200],
                        "type": "integer",
                    }
                ],
            },
            "required": False,
        },
    ]
