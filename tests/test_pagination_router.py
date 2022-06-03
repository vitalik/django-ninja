from typing import List

from ninja import NinjaAPI, Schema
from ninja.pagination import RouterPaginated
from ninja.testing import TestClient

api = NinjaAPI(default_router=RouterPaginated())


class ItemSchema(Schema):
    id: int


@api.get("/items", response=List[ItemSchema])
def items(request):
    return [{"id": i} for i in range(1, 51)]


@api.get("/items_nolist", response=ItemSchema)
def items_nolist(request):
    return {"id": 1}


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
    print(response)
    assert response == {"items": [{"id": 6}], "count": 50}


def test_for_NON_list_reponse():
    parameters = api.get_openapi_schema()["paths"]["/api/items_nolist"]["get"][
        "parameters"
    ]
    print(parameters)
    assert parameters == []
