from datetime import date
from typing import Union
from client import NinjaClient
from ninja import Router

router = Router()


@router.get("/test")
def view(request, value: Union[date, str]):
    return [value, type(value).__name__]


client = NinjaClient(router)


def test_union():
    assert client.get("/test?value=today").json() == ["today", "str"]
    assert client.get("/test?value=2020-01-15").json() == ["2020-01-15", "date"]
    # TODO: test also schema
