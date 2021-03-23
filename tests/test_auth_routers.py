from ninja import NinjaAPI, Router
from ninja.security import APIKeyQuery
from client import NinjaClient


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


client = NinjaClient(api)


def test_router_auth():
    assert client.get("/r1/test").status_code == 401
    assert client.get("/r2/test").status_code == 401

    assert client.get("/r1/test?key=one").status_code == 200
    assert client.get("/r2/test?key=two").status_code == 200

    assert client.get("/r1/test?key=two").status_code == 401
    assert client.get("/r2/test?key=one").status_code == 401

    assert client.get("/r2/child/test").status_code == 401
    assert client.get("/r2/child/test?key=two-child").status_code == 200
