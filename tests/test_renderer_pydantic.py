import datetime
from typing import Any, Optional

from django.utils.translation import gettext_lazy
from pydantic import Field

from ninja import NinjaAPI, Schema, Status
from ninja.renderers import PydanticJSONRenderer
from ninja.testing import TestClient

CREATED = datetime.datetime(2024, 1, 2, 3, 4, 5, tzinfo=datetime.timezone.utc)


class Item(Schema):
    id: int
    created: datetime.datetime
    full_name: str = Field(alias="fullName")
    note: Optional[str] = None


class ItemWithSecret(Item):
    secret: str


class Obj:
    def __init__(self, id):
        self.id = id
        self.created = CREATED
        self.fullName = f"name {id}"
        self.note = None


api = NinjaAPI(renderer=PydanticJSONRenderer())


@api.get("/items", response=list[Item])
def items(request):
    return [Obj(1), Obj(2)]


@api.get("/items-by-alias", response=list[Item], by_alias=True, exclude_none=True)
def items_by_alias(request):
    return [Obj(1)]


@api.get("/instance", response=Item)
def instance(request):
    # only the declared schema's fields may be sent
    return ItemWithSecret(id=1, created=CREATED, fullName="a", secret="s")


@api.post("/created", response={201: Item})
def created(request):
    return Status(201, Obj(3))


@api.get("/untyped")
def untyped(request):
    return {"when": CREATED, "lazy": gettext_lazy("hello"), "text": "Grüße"}


@api.get("/any", response=Any)
def any_value(request):
    return {"lazy": gettext_lazy("hello")}


@api.get("/square")
def square(request, n: int):
    return n * n


client = TestClient(api)


class NoRenderRenderer(PydanticJSONRenderer):
    def render(self, request, data, *, response_status):
        raise AssertionError("responses with a schema must not reach render()")


api_no_render = NinjaAPI(renderer=NoRenderRenderer())
api_no_render.get("/items", response=list[Item])(items)
api_no_render.get("/instance", response=Item)(instance)


def test_typed_response():
    response = client.get("/items")
    assert response.status_code == 200
    assert response["Content-Type"] == "application/json; charset=utf-8"
    assert response.content == (
        b'[{"id":1,"created":"2024-01-02T03:04:05Z","full_name":"name 1","note":null},'
        b'{"id":2,"created":"2024-01-02T03:04:05Z","full_name":"name 2","note":null}]'
    )


def test_dump_options():
    response = client.get("/items-by-alias")
    assert response.json() == [
        {"id": 1, "created": "2024-01-02T03:04:05Z", "fullName": "name 1"}
    ]


def test_model_instance():
    response = client.get("/instance")
    assert response.json() == {
        "id": 1,
        "created": "2024-01-02T03:04:05Z",
        "full_name": "a",
        "note": None,
    }


def test_status():
    response = client.post("/created")
    assert response.status_code == 201
    assert response.json()["id"] == 3


def test_untyped_response():
    response = client.get("/untyped")
    assert response.content == (
        '{"when":"2024-01-02T03:04:05Z","lazy":"hello","text":"Grüße"}'.encode()
    )


def test_fallback_in_typed_response():
    assert client.get("/any").json() == {"lazy": "hello"}


def test_error_response():
    response = client.get("/square?n=x")
    assert response.status_code == 422
    assert response.json()["detail"][0]["loc"] == ["query", "n"]


def test_schema_responses_skip_render():
    no_render_client = TestClient(api_no_render)
    assert no_render_client.get("/items").json()[0]["id"] == 1
    assert no_render_client.get("/instance").json()["id"] == 1
