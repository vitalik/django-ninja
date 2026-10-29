"""api.add_router(auth=/throttle=) must also override the mounted router's own
settings for its nested routers (regression from #1622)."""

import pytest
from django.core.cache import cache

from ninja import NinjaAPI, Router
from ninja.security import APIKeyQuery
from ninja.testing import TestClient
from ninja.throttling import AnonRateThrottle


class Key(APIKeyQuery):
    def __init__(self, value):
        self.value = value
        super().__init__()

    def authenticate(self, request, key):
        if key == self.value:
            return key


def make_router(own_auth):
    parent = Router(auth=own_auth)
    child = Router()

    @parent.get("/")
    def parent_op(request):
        return {"auth": request.auth}

    @child.get("/")
    def child_op(request):
        return {"auth": request.auth}

    parent.add_router("/child", child)
    return parent


@pytest.mark.parametrize("own_auth", [Key("customer"), None])
def test_mount_auth_overrides_router_auth_for_children(own_auth):
    api = NinjaAPI()
    api.add_router("/admin", make_router(own_auth), auth=Key("admin"))
    client = TestClient(api)

    for path in ["/admin/", "/admin/child/"]:
        assert client.get(path).status_code == 401
        assert client.get(path + "?key=customer").status_code == 401
        assert client.get(path + "?key=admin").json() == {"auth": "admin"}


def test_same_router_mounted_with_different_auth():
    router = make_router(Key("customer"))
    api = NinjaAPI()
    api.add_router("/admin", router, auth=Key("admin"), url_name_prefix="admin")
    api.add_router("/shop", router, url_name_prefix="shop")
    client = TestClient(api)

    assert client.get("/admin/child/?key=customer").status_code == 401
    assert client.get("/admin/child/?key=admin").status_code == 200
    assert client.get("/shop/child/?key=customer").status_code == 200
    assert client.get("/shop/child/?key=admin").status_code == 401


def test_mount_throttle_overrides_router_throttle_for_children():
    cache.clear()
    api = NinjaAPI()
    router = Router(throttle=AnonRateThrottle("100/min"))
    child = Router()

    @child.get("/")
    def child_op(request):
        return "ok"

    router.add_router("/child", child)
    api.add_router("/r", router, throttle=AnonRateThrottle("1/min"))
    client = TestClient(api)

    assert client.get("/r/child/").status_code == 200
    assert client.get("/r/child/").status_code == 429
