# The goal of this file is to test that mypy "likes" all the combinations of parametrization
from typing import Any

from django.http import HttpRequest
from typing_extensions import Annotated

from ninja import Body, NinjaAPI, Schema


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
    pass


@api.post("/new_way")
def new_way(request: HttpRequest, data: Body[Payload]) -> Any:
    data.s.capitalize()
    pass
