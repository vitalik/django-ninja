from datetime import date
from enum import Enum
from json import encoder
from pydantic import BaseModel
from ninja import NinjaAPI
from client import NinjaClient


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


client = NinjaClient(api)


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


def test_schema():
    schema = api.get_openapi_schema()

    from pprint import pprint

    pprint(schema)

    booking_shchema = schema["components"]["schemas"]["Booking"]
    assert booking_shchema["properties"]["room"] == {
        "$ref": "#/components/schemas/RoomEnum"
    }
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
        "required": True,
        "schema": {
            "title": "RoomEnum",
            "description": "An enumeration.",
            "enum": ["double", "twin", "single"],
            "type": "string",
        },
    }
