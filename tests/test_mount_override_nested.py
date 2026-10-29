"""Mount-level auth/throttle overrides: they must reach nested routers and stay
isolated per mount (regressions from #1622)."""

import pytest
from django.core.cache import cache

from ninja import NinjaAPI, Router
from ninja.constants import NOT_SET
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


def make_shared_child():
    child = Router()

    @child.get("/")
    def child_op(request):
        return {"auth": request.auth}

    return child


def test_shared_child_public_mount_does_not_unprotect_inherited_auth():
    # GHSA-w84h-fgmh-gcg9
    shared = make_shared_child()
    protected = Router(auth=Key("admin"))
    protected.add_router("/child", shared)
    public = Router()
    public.add_router("/child", shared, auth=None)

    api = NinjaAPI()
    api.add_router("/protected", protected)
    api.add_router("/public", public)
    client = TestClient(api)

    assert client.get("/protected/child/").status_code == 401
    assert client.get("/protected/child/?key=admin").json() == {"auth": "admin"}
    assert client.get("/public/child/").status_code == 200


def test_shared_child_public_mount_does_not_unprotect_explicit_auth():
    # GHSA-8824-xgqv-rgm4
    shared = make_shared_child()
    protected = Router()
    protected.add_router("/child", shared, auth=Key("admin"))
    public = Router()
    public.add_router("/child", shared, auth=None)

    api = NinjaAPI()
    api.add_router("/protected", protected)
    api.add_router("/public", public)
    client = TestClient(api)

    assert client.get("/protected/child/").status_code == 401
    assert client.get("/protected/child/?key=admin").json() == {"auth": "admin"}
    assert client.get("/public/child/").status_code == 200


def test_router_add_router_does_not_mutate_child():
    child = make_shared_child()
    parent = Router()
    parent.add_router("/child", child, auth=None, throttle=AnonRateThrottle("1/min"))

    assert child.auth is NOT_SET
    assert child.throttle is NOT_SET


def test_router_add_router_auth_override_reaches_grandchildren():
    child = make_shared_child()
    grandchild = make_shared_child()
    child.add_router("/grand", grandchild)
    parent = Router()
    parent.add_router("/child", child, auth=Key("admin"))

    api = NinjaAPI()
    api.add_router("/p", parent)
    client = TestClient(api)

    assert client.get("/p/child/grand/").status_code == 401
    assert client.get("/p/child/grand/?key=admin").status_code == 200


def test_shared_child_throttle_override_is_per_mount():
    cache.clear()
    shared = make_shared_child()
    strict = Router()
    strict.add_router("/child", shared, throttle=AnonRateThrottle("1/min"))
    relaxed = Router()
    relaxed.add_router("/child", shared)

    api = NinjaAPI()
    api.add_router("/strict", strict)
    api.add_router("/relaxed", relaxed)
    client = TestClient(api)

    assert client.get("/strict/child/").status_code == 200
    assert client.get("/strict/child/").status_code == 429
    for _ in range(3):
        assert client.get("/relaxed/child/").status_code == 200
