from ninja import Body, Form, NinjaAPI
from ninja.testing import TestClient

api = NinjaAPI()

# testing Body marker:


@api.post("/task")
def create_task(request, start: int = Body(...), end: int = Body(...)):
    return [start, end]


@api.post("/task2")
def create_task2(request, start: int = Body(2), end: int = Form(1)):
    return [start, end]


def test_body():
    client = TestClient(api)
    assert client.post("/task", json={"start": 1, "end": 2}).json() == [1, 2]


def test_body_form():
    client = TestClient(api)
    assert client.post("/task2", POST={"start": "1", "end": "2"}).json() == [1, 2]
    assert client.post("/task2").json() == [2, 1]
