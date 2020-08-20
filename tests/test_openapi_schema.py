import pytest
from ninja import NinjaAPI
from django.test import Client


api = NinjaAPI()


@api.get("/test")
def method(request, query: str, count: int):
    return [query, count]


def test_schema(client: Client):
    assert client.get("/api/").status_code == 404
    assert client.get("/api/docs").status_code == 200
    assert client.get("/api/openapi.json").status_code == 200
    # TODO: more schema tests
