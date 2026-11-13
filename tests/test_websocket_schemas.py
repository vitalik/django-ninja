import json
from datetime import date
from typing import List

import pydantic
from typing_extensions import Annotated
from ws_util import unique_namespace

from ninja import NinjaAPI, Schema, WebSocket
from ninja.renderers import BaseRenderer
from ninja.testing import TestClient


class Item(Schema):
    name: str
    qty: int = 1


class ItemOut(Schema):
    name: str
    created: date


class OrmLike:
    def __init__(self, name):
        self.name = name
        self.created = date(2024, 5, 6)
        self.secret = "hidden"


def make_client():
    api = NinjaAPI(urls_namespace=unique_namespace())

    @api.websocket("/items")
    async def items(websocket: WebSocket):
        await websocket.accept()
        async for item in websocket.iter_json(schema=Item):
            assert isinstance(item, Item)
            await websocket.send_json(item)  # pydantic model serialized as is

    @api.websocket("/bulk")
    async def bulk(websocket: WebSocket):
        await websocket.accept()
        try:
            items = await websocket.receive_json(schema=List[Item])
        except pydantic.ValidationError as e:
            await websocket.send_json({"errors": len(e.errors())})
            return
        await websocket.send_json(sum(i.qty for i in items), mode="binary")

    @api.websocket("/orm")
    async def orm(websocket: WebSocket):
        await websocket.accept()
        await websocket.send_json(OrmLike("a"), schema=ItemOut)
        await websocket.send_json([OrmLike("b")], schema=List[ItemOut])

    @api.websocket("/unhashable")
    async def unhashable(websocket: WebSocket):
        await websocket.accept()
        value = await websocket.receive_json(
            "binary", schema=Annotated[int, {"meta": "unhashable"}]
        )
        await websocket.send_json(value + 1)

    return TestClient(api)


def test_iter_json_with_schema():
    with make_client().websocket_connect("/items") as ws:
        ws.send_json({"name": "x"})
        assert ws.receive_json() == {"name": "x", "qty": 1}
        ws.send_json({"name": "y", "qty": 3})
        assert ws.receive_json() == {"name": "y", "qty": 3}


def test_receive_list_schema_and_errors():
    client = make_client()
    with client.websocket_connect("/bulk") as ws:
        ws.send_json([{"name": "a", "qty": 2}, {"name": "b", "qty": 5}])
        assert ws.receive_json(mode="binary") == 7

    with client.websocket_connect("/bulk") as ws:
        ws.send_json([{"qty": "x"}])
        assert ws.receive_json() == {"errors": 2}


def test_send_json_with_schema_from_attributes():
    with make_client().websocket_connect("/orm") as ws:
        assert ws.receive_json() == {"name": "a", "created": "2024-05-06"}
        assert ws.receive_json() == [{"name": "b", "created": "2024-05-06"}]


def test_unhashable_schema():
    with make_client().websocket_connect("/unhashable") as ws:
        ws.send_json(41, mode="binary")
        assert ws.receive_json() == 42


class CompactBytesRenderer(BaseRenderer):
    media_type = "application/json"

    def render(self, request, data, *, response_status):
        return json.dumps(data, separators=(",", ":")).encode() + b" "


class XMLRenderer(BaseRenderer):
    media_type = "text/xml"

    def render(self, request, data, *, response_status):
        return "<xml/>"  # pragma: no cover


def renderer_client(renderer):
    api = NinjaAPI(urls_namespace=unique_namespace(), renderer=renderer)

    @api.websocket("/ws")
    async def ws(websocket: WebSocket):
        await websocket.accept()
        await websocket.send_json({"a": [1, 2], "ñ": True})

    return TestClient(api)


def test_send_json_uses_api_json_renderer():
    with renderer_client(CompactBytesRenderer()).websocket_connect("/ws") as ws:
        assert ws.receive_text() == '{"a":[1,2],"\\u00f1":true} '


def test_send_json_ignores_non_json_renderer():
    with renderer_client(XMLRenderer()).websocket_connect("/ws") as ws:
        assert ws.receive_text() == '{"a":[1,2],"ñ":true}'
