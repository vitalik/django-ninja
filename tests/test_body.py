from ninja import NinjaAPI, Body
from client import NinjaClient


api = NinjaAPI()

# testing Body marker:


@api.post("/task")
def create_task(request, start: int = Body(...), end: int = Body(...)):
    return [start, end]


def test_body():
    client = NinjaClient(api)
    assert client.post("/task", json={"start": 1, "end": 2}).json() == [1, 2]
