from ninja import NinjaAPI, Router
import pytest
from client import NinjaClient

second_router = Router()
first_router = Router()
api = NinjaAPI()


@api.get("/endpoint")
def global_op(request):
    pass


@first_router.get("/endpoint")
def router_op(request):
    pass


@second_router.get("/endpoint")
def router_op(request):
    pass


first_router.add_router("/second", second_router)
api.add_router("/first", first_router)


client = NinjaClient(api)


@pytest.mark.parametrize(
    "path,expected_status,expected_response",
    [
        ("/endpoint", 200, None),
        ("/first/endpoint", 200, None),
        ("/first/second/endpoint", 200, None),
    ],
)
def test_inheritance_responses(path, expected_status, expected_response):
    response = client.get(path)
    assert response.status_code == expected_status, response.content
    assert response.json() == expected_response
