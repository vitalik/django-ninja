from docs.src.index001 import api
from client import NinjaClient


client = NinjaClient(api)


def test_api():
    response = client.get("/add?a=1&b=2")
    assert response.json() == {"result": 3}
