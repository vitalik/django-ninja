import pytest

from ninja import NinjaAPI, Router
from ninja.testing import TestClient

api = NinjaAPI()


@api.get("/endpoint")
# view->api
def global_op(request):
    return "global"


first_router = Router()


@first_router.get("/endpoint_1")
# view->router, router->api
def router_op1(request):
    return "first 1"


second_router_one = Router()


@second_router_one.get("endpoint_1")
# view->router2, router2->router1, router1->api
def router_op2(request):
    return "second 1"


second_router_two = Router()


@second_router_two.get("endpoint_2")
# view->router2, router2->router1, router1->api
def router2_op3(request):
    return "second 2"


first_router.add_router("/second", second_router_one, tags=["one"])
first_router.add_router("/second", second_router_two, tags=["two"])
api.add_router("/first", first_router, tags=["global"])


@first_router.get("endpoint_2")
# router->api, view->router
def router1_op1(request):
    return "first 2"


@second_router_one.get("endpoint_3")
# router2->router1, router1->api, view->router2
def router21_op3(request, path_param: int = None):
    return "second 3" if path_param is None else f"second 3: {path_param}"


second_router_three = Router()


@second_router_three.get("endpoint_4")
# router1->api, view->router2, router2->router1
def router_op3(request, path_param: int = None):
    return "second 4" if path_param is None else f"second 4: {path_param}"


first_router.add_router("/second", second_router_three, tags=["three"])


client = TestClient(api)


@pytest.mark.parametrize(
    "path,expected_status,expected_response",
    [
        ("/endpoint", 200, "global"),
        ("/first/endpoint_1", 200, "first 1"),
        ("/first/endpoint_2", 200, "first 2"),
        ("/first/second/endpoint_1", 200, "second 1"),
        ("/first/second/endpoint_2", 200, "second 2"),
        ("/first/second/endpoint_3", 200, "second 3"),
        ("/first/second/endpoint_4", 200, "second 4"),
    ],
)
def test_inheritance_responses(path, expected_status, expected_response):
    response = client.get(path)
    assert response.status_code == expected_status, response.content
    assert response.json() == expected_response


def test_tags():
    schema = api.get_openapi_schema()
    # print(schema)
    glob = schema["paths"]["/api/first/endpoint_1"]["get"]
    assert glob["tags"] == ["global"]

    e1 = schema["paths"]["/api/first/second/endpoint_1"]["get"]
    assert e1["tags"] == ["one"]

    e2 = schema["paths"]["/api/first/second/endpoint_2"]["get"]
    assert e2["tags"] == ["two"]
