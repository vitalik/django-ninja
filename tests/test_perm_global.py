import pytest

from ninja import NinjaAPI, Router
from ninja.security import BasePermission
from ninja.testing import TestClient


class DummyPermission(BasePermission):
    def has_permission(self, request, permission):
        print("Test")
        return permission == "dummy"


api = NinjaAPI(perm=DummyPermission("dummy"))


@api.get("/default")
def default(request):
    return "test"


@api.api_operation(["POST", "PATCH"], "/multi-method-no-perm")
def multi_no_perm(request):
    return "test"


@api.api_operation(
    ["POST", "PATCH"], "/multi-method-perm", perm=DummyPermission("Test")
)
def multi_perm(request):
    return "test"


# ---- router ------------------------

router = Router()


@router.get("/router-operation")  # should come from global perm
def router_operation(request):
    return "test"


@router.get("/router-operation-perm", perm=DummyPermission("Test"))
def router_operation_perm(request):
    return "test"


api.add_router("", router)

# ---- end router --------------------


@api.get("/type-error", perm="dummy")
def type_error():
    return "test"


client = TestClient(api)


def test_multi():
    assert client.get("/default").status_code == 200
    assert client.post("/multi-method-no-perm").status_code == 200
    assert client.patch("/multi-method-no-perm").status_code == 200
    assert client.post("/multi-method-perm").status_code == 403
    assert client.patch("/multi-method-perm").status_code == 403


def test_router_perm():
    assert client.get("/router-operation").status_code == 200
    assert client.get("/router-operation-perm").status_code == 403


def test_type_error():
    with pytest.raises(TypeError):
        client.get("/type-error").status_code == 403
