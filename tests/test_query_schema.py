from datetime import datetime
from enum import IntEnum

from pydantic import BaseModel, Field

from ninja import NinjaAPI, Query, Schema
from ninja.testing.client import TestClient


class Range(IntEnum):
    TWENTY = 20
    FIFTY = 50
    TWO_HUNDRED = 200


class Filter(BaseModel):
    to_datetime: datetime = Field(alias="to")
    from_datetime: datetime = Field(alias="from")
    range: Range = Range.TWENTY


class Data(Schema):
    an_int: int = Field(alias="int", default=0)
    a_float: float = Field(alias="float", default=1.5)


api = NinjaAPI()


@api.get("/test")
def query_params_schema(request, filters: Filter = Query(...)):
    return filters.model_dump()


@api.get("/test-mixed")
def query_params_mixed_schema(
    request,
    query1: int,
    query2: int = 5,
    filters: Filter = Query(...),
    data: Data = Query(...),
):
    return dict(
        query1=query1,
        query2=query2,
        filters=filters.model_dump(),
        data=data.model_dump(),
    )


def test_request():
    client = TestClient(api)
    response = client.get("/test?from=1&to=2&range=20&foo=1&range2=50")
    print("!", response.json())
    assert response.json() == {
        "to_datetime": "1970-01-01T00:00:02Z",
        "from_datetime": "1970-01-01T00:00:01Z",
        "range": 20,
    }

    response = client.get("/test?from=1&to=2&range=21")
    assert response.status_code == 422


def test_request_mixed():
    client = TestClient(api)
    response = client.get(
        "/test-mixed?from=1&to=2&range=20&foo=1&range2=50&query1=2&int=3&float=1.6"
    )
    print(response.json())
    assert response.json() == {
        "data": {"a_float": 1.6, "an_int": 3},
        "filters": {
            "from_datetime": "1970-01-01T00:00:01Z",
            "range": 20,
            "to_datetime": "1970-01-01T00:00:02Z",
        },
        "query1": 2,
        "query2": 5,
    }

    response = client.get(
        "/test-mixed?from=1&to=2&range=20&foo=1&range2=50&query1=2&query2=10"
    )
    print(response.json())
    assert response.json() == {
        "data": {"a_float": 1.5, "an_int": 0},
        "filters": {
            "from_datetime": "1970-01-01T00:00:01Z",
            "range": 20,
            "to_datetime": "1970-01-01T00:00:02Z",
        },
        "query1": 2,
        "query2": 10,
    }

    response = client.get("/test-mixed?from=1&to=2")
    assert response.status_code == 422


def test_request_query_params_using_basemodel():
    class Foo(BaseModel):
        start: int
        optional: int = 42

    temp_api = NinjaAPI()

    @temp_api.get("/foo")
    def view(request, foo: Foo = Query(...)):
        return foo.model_dump()

    client = TestClient(temp_api)
    resp = client.get("/foo?start=1")

    assert resp.status_code == 200
    assert resp.json() == {"start": 1, "optional": 42}


def test_schema():
    schema = api.get_openapi_schema()
    params = schema["paths"]["/api/test"]["get"]["parameters"]
    print(params)
    assert params == [
        {
            "in": "query",
            "name": "to",
            "schema": {"format": "date-time", "title": "To", "type": "string"},
            "required": True,
        },
        {
            "in": "query",
            "name": "from",
            "schema": {"format": "date-time", "title": "From", "type": "string"},
            "required": True,
        },
        {
            "in": "query",
            "name": "range",
            "schema": {
                "allOf": [{"enum": [20, 50, 200], "title": "Range", "type": "integer"}],
                "default": 20,
            },
            "required": False,
        },
    ]


def test_schema_all_of_no_ref():
    details = {
        "default": 1,
        "allOf": [
            {"$ref": "#/components/schemas/Type"},
            {"no-ref-here": "xyzzy"},
        ],
    }
    definitions = {"Type": {"title": "Best Type Ever!"}}

    from ninja.openapi.schema import resolve_allOf

    resolve_allOf(details, definitions)

    assert details == {
        "default": 1,
        "allOf": [{"title": "Best Type Ever!"}, {"no-ref-here": "xyzzy"}],
    }
