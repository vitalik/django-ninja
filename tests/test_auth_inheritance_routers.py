import pytest

from ninja import NinjaAPI, Router
from ninja.security import APIKeyQuery
from ninja.testing import TestClient


class Auth(APIKeyQuery):
    def __init__(self, secret):
        self.secret = secret
        super().__init__()

    def authenticate(self, request, key):
        if key == self.secret:
            return key


api = NinjaAPI(auth=Auth("api_auth"))

r1 = Router()
r2 = Router()
r3 = Router()
r4 = Router()

o3 = Router(auth=None)
o4 = Router()

api.add_router("/r1", r1, auth=Auth("r1_auth"))
r1.add_router("/r2", r2)
r2.add_router("/r3", r3)
r3.add_router("/r4", r4, auth=Auth("r4_auth"))
r2.add_router("/o3", o3)
o3.add_router("/o4", o4)

client = TestClient(api)


@r1.get("/")
def op1(request):
    return request.auth


@r2.get("/")
def op2(request):
    return request.auth


@r3.get("/")
def op3(request):
    return request.auth


@r4.get("/")
def op4(request):
    return request.auth


@r3.get("/op5", auth=Auth("op5_auth"))
def op5(request):
    return request.auth


@o3.get("/")
def op_o3(request):
    assert request.auth is None
    return "ok"


@o4.get("/")
def op_o4(request):
    assert request.auth is None
    return "ok"


@pytest.mark.parametrize(
    "route, status_code",
    [
        ("/r1/", 401),
        ("/r1/r2/", 401),
        ("/r1/r2/r3/", 401),
        ("/r1/r2/r3/r4/", 401),
        ("/r1/r2/r3/op5", 401),
        ("/r1/?key=r1_auth", 200),
        ("/r1/r2/?key=r1_auth", 200),
        ("/r1/r2/r3/?key=r1_auth", 200),
        ("/r1/r2/r3/r4/?key=r4_auth", 200),
        ("/r1/r2/r3/op5?key=op5_auth", 200),
        ("/r1/r2/r3/r4/?key=r1_auth", 401),
        ("/r1/r2/r3/op5?key=r1_auth", 401),
        ("/r1/r2/o3/", 200),
        ("/r1/r2/o3/o4/", 200),
    ],
)
def test_router_inheritance_auth(route, status_code):
    assert client.get(route).status_code == status_code
