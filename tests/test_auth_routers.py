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


api = NinjaAPI()

r1 = Router()
r2 = Router()
r2_1 = Router()


@r1.get("/test")
def operation1(request):
    return request.auth


@r2.get("/test")
def operation2(request):
    return request.auth


@r2_1.get("/test")
def operation3(request):
    return request.auth


r2.add_router("/child", r2_1, auth=Auth("two-child"))
api.add_router("/r1", r1, auth=Auth("one"))
api.add_router("/r2", r2, auth=Auth("two"))


client = TestClient(api)


@pytest.mark.parametrize(
    "route, status_code",
    [
        ("/r1/test", 401),
        ("/r2/test", 401),
        ("/r1/test?key=one", 200),
        ("/r2/test?key=two", 200),
        ("/r1/test?key=two", 401),
        ("/r2/test?key=one", 401),
        ("/r2/child/test", 401),
        ("/r2/child/test?key=two-child", 200),
    ],
)
def test_router_auth(route, status_code):
    assert client.get(route).status_code == status_code
