# The goal of this file is to test that mypy "likes" all the combinations of parametrization
from typing import Any, List

from django.http import HttpRequest
from typing_extensions import Annotated

from ninja import (
    Body,
    BodyEx,
    NinjaAPI,
    P,
    Schema,
    Status,
    WebSocket,
    WebSocketException,
)
from ninja.streaming import JSONL, SSE
from ninja.websockets import WebSocketClose


class Payload(Schema):
    x: int
    y: float
    s: str


api = NinjaAPI()


@api.post("/old_way")
def old_way(request: HttpRequest, data: Payload = Body()) -> Any:
    data.s.capitalize()


@api.post("/annotated_way")
def annotated_way(request: HttpRequest, data: Annotated[Payload, Body()]) -> Any:
    data.s.capitalize()


@api.post("/new_way")
def new_way(request: HttpRequest, data: Body[Payload]) -> Any:
    data.s.capitalize()


@api.post("/new_way_ex")
def new_way_ex(request: HttpRequest, data: BodyEx[Payload, P(title="A title")]) -> Any:
    data.s.find("")


# -- Status generic --


@api.post("/status_generic")
def status_generic(request: HttpRequest) -> Status[dict]:
    return Status(200, {"key": "value"})


@api.post("/status_generic_schema")
def status_generic_schema(request: HttpRequest) -> Status[Payload]:
    return Status(200, Payload(x=1, y=2.0, s="test"))


# -- Streaming generics --


@api.get("/sse_stream", response=SSE[Payload])
def sse_stream(request: HttpRequest) -> Any:
    yield {"x": 1, "y": 2.0, "s": "test"}


@api.get("/jsonl_stream", response=JSONL[Payload])
def jsonl_stream(request: HttpRequest) -> Any:
    yield {"x": 1, "y": 2.0, "s": "test"}


# -- WebSockets --


@api.websocket("/ws/{room}")
async def websocket_typing(websocket: WebSocket, room: int) -> None:
    await websocket.accept()
    payload = await websocket.receive_json(schema=Payload)
    payload.s.capitalize()
    payloads = await websocket.receive_json("binary", schema=List[Payload])
    payloads[0].s.capitalize()
    async for item in websocket.iter_json(schema=Payload):
        item.s.capitalize()
    raw: Any = await websocket.receive_json()
    await websocket.send_json(raw, schema=Payload)
    if room < 0:
        raise WebSocketException(code=WebSocketClose.POLICY_VIOLATION, reason="bad")
