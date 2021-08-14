from ninja import NinjaAPI, Router
from ninja.security import BasePermission
from ninja.testing import TestClient


class DummyPermission(BasePermission):
    def has_permission(self, request, permission):
        print("Test")
        return permission == "dummy"


api = NinjaAPI()

r1 = Router()
r2 = Router()
r2_1 = Router()


@r1.get("/test")
def operation1(request):
    return "test"


@r2.get("/test")
def operation2(request):
    return "test"


@r2_1.get("/test")
def operation3(request):
    return "test"


r2.add_router("/child", r2_1, perm=None)
api.add_router("/r1", r1, perm=DummyPermission("dummy"))
api.add_router("/r2", r2, perm=DummyPermission("Test"))


client = TestClient(api)


def test_router_perm():
    assert client.get("/r1/test").status_code == 200
    assert client.get("/r2/test").status_code == 403
    assert client.get("/r2/child/test").status_code == 200
