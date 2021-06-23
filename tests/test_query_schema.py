from datetime import datetime
from enum import IntEnum

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
