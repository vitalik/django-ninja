from ninja import NinjaAPI, Router
import pytest
from client import NinjaClient

api = NinjaAPI()


@api.get("/endpoint")
def global_op(request):
    return "global"


first_router = Router()


@first_router.get("/endpoint")
def router_op1(request):
    return "first"


second_router_one = Router()


@second_router_one.get("endpoint_1")
def router_op2(request):
    return "second 1"


second_router_two = Router()


@second_router_two.get("endpoint_2")
def router_op3(request):
    return "second 2"


first_router.add_router("/second", second_router_one, tags=["one"])
first_router.add_router("/second", second_router_two, tags=["two"])
api.add_router("/first", first_router, tags=["global"])


client = NinjaClient(api)


@pytest.mark.parametrize(
    "path,expected_status,expected_response",
    [
        ("/endpoint", 200, "global"),
        ("/first/endpoint", 200, "first"),
        ("/first/second/endpoint_1", 200, "second 1"),
        ("/first/second/endpoint_2", 200, "second 2"),
    ],
)
def test_inheritance_responses(path, expected_status, expected_response):
    response = client.get(path)
    assert response.status_code == expected_status, response.content
    assert response.json() == expected_response


def test_tags():
    schema = api.get_openapi_schema()
    # print(schema)
    glob = schema["paths"]["/api/first/endpoint"]["get"]
    assert glob["tags"] == ["global"]

    e1 = schema["paths"]["/api/first/second/endpoint_1"]["get"]
    assert e1["tags"] == ["one"]

    e2 = schema["paths"]["/api/first/second/endpoint_2"]["get"]
    assert e2["tags"] == ["two"]
