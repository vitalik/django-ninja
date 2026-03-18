"""
Regression tests for issue #1699: Auth override at router level via add_router().

Verifies that auth passed to api.add_router("/prefix", router, auth=SomeAuth())
correctly protects all endpoints under that router, including child routers.
"""

import base64
from typing import Dict

import pytest

from ninja import NinjaAPI, Router
from ninja.security import APIKeyQuery, HttpBasicAuth
from ninja.testing import TestClient


class KeyAuth(APIKeyQuery):
    def __init__(self, secret: str):
        self.secret = secret
        super().__init__()

    def authenticate(self, request, key):
        if key == self.secret:
            return key


class BasicAuth(HttpBasicAuth):
    def authenticate(self, request, username: str, password: str):
        if username == "admin" and password == "secret":
            return username


def _basic_auth_header() -> Dict[str, str]:
    creds = base64.b64encode(b"admin:secret").decode()
    return {"Authorization": f"Basic {creds}"}


# --- Test 1: Basic auth override via add_router with HttpBasicAuth ---


def test_add_router_auth_override_basic_auth():
    api = NinjaAPI()
    router = Router()

    @router.get("/endpoint")
    def endpoint(request):
        return {"user": request.auth}

    api.add_router("/events", router, auth=BasicAuth())
    client = TestClient(api)

    assert client.get("/events/endpoint").status_code == 401
    assert (
        client.get("/events/endpoint", headers=_basic_auth_header()).status_code == 200
    )


# --- Test 2: Auth override with APIKeyQuery ---


def test_add_router_auth_override_apikey():
    api = NinjaAPI()
    router = Router()

    @router.get("/endpoint")
    def endpoint(request):
        return {"auth": request.auth}

    api.add_router("/items", router, auth=KeyAuth("mykey"))
    client = TestClient(api)

    assert client.get("/items/endpoint").status_code == 401
    assert client.get("/items/endpoint?key=wrong").status_code == 401
    assert client.get("/items/endpoint?key=mykey").status_code == 200


# --- Test 3: Auth override propagates to child routers ---


def test_add_router_auth_propagates_to_children():
    api = NinjaAPI()
    parent = Router()
    child = Router()

    @parent.get("/parent-op")
    def parent_op(request):
        return {"auth": request.auth}

    @child.get("/child-op")
    def child_op(request):
        return {"auth": request.auth}

    parent.add_router("/child", child)
    api.add_router("/base", parent, auth=KeyAuth("parentkey"))
    client = TestClient(api)

    assert client.get("/base/parent-op").status_code == 401
    assert client.get("/base/parent-op?key=parentkey").status_code == 200
    assert client.get("/base/child/child-op").status_code == 401
    assert client.get("/base/child/child-op?key=parentkey").status_code == 200


# --- Test 4: Deeply nested routers (3 levels) ---


def test_add_router_auth_deeply_nested():
    api = NinjaAPI()
    r1 = Router()
    r2 = Router()
    r3 = Router()

    @r1.get("/op1")
    def op1(request):
        return {"auth": request.auth}

    @r2.get("/op2")
    def op2(request):
        return {"auth": request.auth}

    @r3.get("/op3")
    def op3(request):
        return {"auth": request.auth}

    r2.add_router("/r3", r3)
    r1.add_router("/r2", r2)
    api.add_router("/r1", r1, auth=KeyAuth("deep"))
    client = TestClient(api)

    for path in ["/r1/op1", "/r1/r2/op2", "/r1/r2/r3/op3"]:
        assert client.get(path).status_code == 401
        assert client.get(f"{path}?key=deep").status_code == 200


# --- Test 5: Auth override coexists with API-level auth ---


def test_add_router_auth_overrides_api_auth():
    api = NinjaAPI(auth=KeyAuth("api_key"))
    router = Router()
    unprotected = Router()

    @router.get("/secured")
    def secured(request):
        return {"auth": request.auth}

    @unprotected.get("/default")
    def default_op(request):
        return {"auth": request.auth}

    api.add_router("/custom", router, auth=KeyAuth("router_key"))
    api.add_router("/standard", unprotected)
    client = TestClient(api)

    # Router-level auth takes precedence over API auth
    assert client.get("/custom/secured").status_code == 401
    assert client.get("/custom/secured?key=api_key").status_code == 401
    assert client.get("/custom/secured?key=router_key").status_code == 200

    # Unoverridden router falls back to API auth
    assert client.get("/standard/default").status_code == 401
    assert client.get("/standard/default?key=api_key").status_code == 200


# --- Test 6: add_router(auth=X) overrides Router(auth=None) ---


def test_add_router_auth_overrides_router_auth_none():
    api = NinjaAPI()
    router = Router(auth=None)

    @router.get("/op")
    def op(request):
        return {"auth": request.auth}

    api.add_router("/prefix", router, auth=KeyAuth("override"))
    client = TestClient(api)

    assert client.get("/prefix/op").status_code == 401
    assert client.get("/prefix/op?key=override").status_code == 200


# --- Test 7: Reused router with different auth on different mounts ---


def test_reused_router_different_auth():
    api = NinjaAPI()
    router = Router()

    @router.get("/op")
    def op(request):
        return {"auth": request.auth}

    api.add_router("/mount1", router, auth=KeyAuth("key1"), url_name_prefix="m1")
    api.add_router("/mount2", router, auth=KeyAuth("key2"), url_name_prefix="m2")
    client = TestClient(api)

    # mount1 uses key1
    assert client.get("/mount1/op").status_code == 401
    assert client.get("/mount1/op?key=key1").status_code == 200
    assert client.get("/mount1/op?key=key2").status_code == 401

    # mount2 uses key2
    assert client.get("/mount2/op").status_code == 401
    assert client.get("/mount2/op?key=key2").status_code == 200
    assert client.get("/mount2/op?key=key1").status_code == 401
