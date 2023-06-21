from datetime import date
from enum import Enum
from typing import List, Optional

from pydantic import BaseModel

from ninja import NinjaAPI, Query
from ninja.testing import TestClient


class RoomEnum(str, Enum):
    double = "double"
    twin = "twin"
    single = "single"


class Booking(BaseModel):
    start: date
    end: date
    room: RoomEnum = RoomEnum.double


api = NinjaAPI()


@api.post("/book")
def create_booking(request, booking: Booking):
    return booking


@api.get("/search")
def booking_search(request, room: RoomEnum):
    return {"room": room}


@api.get("/optional")
def enum_optional(
    request, room: Optional[RoomEnum] = Query(None, description="description")
):
    return {"room": room}


@api.get("/list")
def enum_list(request, rooms: List[RoomEnum] = Query(None, description="description")):
    return {"rooms": rooms}


class QueryOnlyEnum(str, Enum):
    one = "one"
    two = "two"


@api.get("/new-list")
def new_enum_list(
    request, q: List[QueryOnlyEnum] = Query(None, description="description")
):
    return {"q": q}


client = TestClient(api)


def test_enums():
    response = client.post(
        "/book", json={"start": "2020-01-01", "end": "2020-01-02", "room": "double"}
    )
    assert response.status_code == 200, response.content
    assert response.json() == {
        "start": "2020-01-01",
        "end": "2020-01-02",
        "room": "double",
    }

    response = client.post(
        "/book", json={"start": "2020-01-01", "end": "2020-01-02", "room": "triple"}
    )
    assert response.status_code == 422

    response = client.get("/search?room=twin")
    assert response.status_code == 200
    assert response.json() == {"room": "twin"}

    response = client.get("/search?room=other")
    assert response.status_code == 422

    response = client.get("/optional?room=twin")
    assert response.status_code == 200

    response = client.get("/optional")
    assert response.status_code == 200
    assert response.json() == {"room": None}

    response = client.get("/list?rooms=twin&rooms=single")
    assert response.status_code == 200
    assert response.json() == {"rooms": ["twin", "single"]}

    response = client.get("/new-list?q=one&q=one")
    assert response.status_code == 200
    assert response.json() == {"q": ["one", "one"]}


def test_schema():
    schema = api.get_openapi_schema()

    booking_schema = schema["components"]["schemas"]["Booking"]
    room_prop = booking_schema["properties"]["room"]

    if "allOf" in room_prop:
        # pydantic 1.7+ change:
        assert room_prop["allOf"] == [{"$ref": "#/components/schemas/RoomEnum"}]
    else:
        assert room_prop == {"$ref": "#/components/schemas/RoomEnum"}

    assert schema["components"]["schemas"]["RoomEnum"] == {
        "description": "An enumeration.",
        "enum": ["double", "twin", "single"],
        "title": "RoomEnum",
        "type": "string",
    }

    book_operation = schema["paths"]["/api/book"]["post"]
    assert book_operation["requestBody"]["content"]["application/json"]["schema"] == {
        "$ref": "#/components/schemas/Booking"
    }

    search_operation = schema["paths"]["/api/search"]["get"]
    room_param = search_operation["parameters"][0]
    assert room_param == {
        "in": "query",
        "name": "room",
        "description": "An enumeration.",
        "required": True,
        "schema": {
            "title": "RoomEnum",
            "description": "An enumeration.",
            "enum": ["double", "twin", "single"],
            "type": "string",
        },
    }

    optional_operation = schema["paths"]["/api/optional"]["get"]
    room_param = optional_operation["parameters"][0]
    assert room_param == {
        "in": "query",
        "name": "room",
        "schema": {
            "description": "description",
            "allOf": [
                {
                    "title": "RoomEnum",
                    "description": "An enumeration.",
                    "enum": ["double", "twin", "single"],
                    "type": "string",
                }
            ],
        },
        "required": False,
        "description": "description",
    }

    assert schema["paths"]["/api/new-list"]["get"]["parameters"][0] == {
        "description": "description",
        "in": "query",
        "name": "q",
        "required": False,
        "schema": {
            "description": "description",
            "items": {
                "description": "An enumeration.",
                "enum": ["one", "two"],
                "title": "QueryOnlyEnum",
                "type": "string",
            },
            "type": "array",
        },
    }
