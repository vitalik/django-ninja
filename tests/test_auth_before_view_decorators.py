"""Authentication must run before view-mode decorators (issue #1646).

View-mode decorators (``add_decorator(..., mode="view")`` and
``@decorate_view``) wrap ``Operation.run``, while authentication used to
run *inside* ``run`` - so decorators executed before auth, saw
``request.auth`` unset, and even ran for requests that were ultimately
rejected with 401.  The operation checks now run in ``PathView`` before
the decorated ``run`` is invoked.
"""

from functools import wraps

import pytest

from ninja import NinjaAPI, Router
from ninja.decorators import decorate_view
from ninja.security import APIKeyHeader
from ninja.testing import TestAsyncClient, TestClient

GOOD = {"X-Key": "secret"}


class CountingKeyAuth(APIKeyHeader):
    param_name = "X-Key"

    def __init__(self, events):
        super().__init__()
        self.events = events

    def authenticate(self, request, key):
        self.events.append("auth")
        if key == "secret":
            return {"tenant": "acme"}
        return None


def recording_view_decorator(events, seen_auth):
    def decorator(func):
        @wraps(func)
        def wrapper(request, *args, **kwargs):
            events.append("decorator")
            seen_auth.append(getattr(request, "auth", None))
            return func(request, *args, **kwargs)

        return wrapper

    return decorator


def test_api_auth_runs_before_view_decorator():
    events, seen_auth = [], []
    api = NinjaAPI(auth=CountingKeyAuth(events), urls_namespace="auth_order_1")
    api.add_decorator(recording_view_decorator(events, seen_auth), mode="view")

    @api.get("/thing")
    def thing(request):
        events.append("view")
        return {"auth": request.auth}

    client = TestClient(api)
    response = client.get("/thing", headers=GOOD)

    assert response.status_code == 200
    assert response.json() == {"auth": {"tenant": "acme"}}
    # the decorator already saw the authenticated identity...
    assert seen_auth == [{"tenant": "acme"}]
    # ...because auth ran first - and exactly once:
    assert events == ["auth", "decorator", "view"]


def test_unauthenticated_request_short_circuits_before_view_decorator():
    events, seen_auth = [], []
    api = NinjaAPI(auth=CountingKeyAuth(events), urls_namespace="auth_order_2")
    api.add_decorator(recording_view_decorator(events, seen_auth), mode="view")

    @api.get("/thing")
    def thing(request):  # pragma: no cover
        events.append("view")
        return {}

    client = TestClient(api)
    response = client.get("/thing")

    assert response.status_code == 401
    # neither the decorator nor the view ran for the rejected request:
    assert events == ["auth"]
    assert seen_auth == []


def test_router_auth_runs_before_router_view_decorator():
    events, seen_auth = [], []
    router = Router(auth=CountingKeyAuth(events))
    router.add_decorator(recording_view_decorator(events, seen_auth), mode="view")

    @router.get("/thing")
    def thing(request):
        return {"auth": request.auth}

    api = NinjaAPI(urls_namespace="auth_order_3")
    api.add_router("/", router)
    client = TestClient(api)

    response = client.get("/thing", headers=GOOD)
    assert response.status_code == 200
    assert seen_auth == [{"tenant": "acme"}]
    assert events == ["auth", "decorator"]


def test_decorate_view_runs_after_auth():
    events, seen_auth = [], []
    api = NinjaAPI(auth=CountingKeyAuth(events), urls_namespace="auth_order_4")

    @api.get("/thing")
    @decorate_view(recording_view_decorator(events, seen_auth))
    def thing(request):
        return {"auth": request.auth}

    client = TestClient(api)

    response = client.get("/thing", headers=GOOD)
    assert response.status_code == 200
    assert seen_auth == [{"tenant": "acme"}]

    events.clear()
    response = client.get("/thing")
    assert response.status_code == 401
    assert events == ["auth"]


def test_view_decorator_can_still_modify_response_after_auth():
    events = []
    api = NinjaAPI(auth=CountingKeyAuth(events), urls_namespace="auth_order_5")

    def header_decorator(func):
        @wraps(func)
        def wrapper(request, *args, **kwargs):
            response = func(request, *args, **kwargs)
            response["X-Decorator"] = "applied"
            return response

        return wrapper

    api.add_decorator(header_decorator, mode="view")

    @api.get("/thing")
    def thing(request):
        return {"ok": True}

    client = TestClient(api)
    response = client.get("/thing", headers=GOOD)
    assert response.status_code == 200
    assert response["X-Decorator"] == "applied"


# --- Async variants (sync/async paths must stay symmetric) ---


def recording_async_view_decorator(events, seen_auth):
    def decorator(func):
        @wraps(func)
        async def wrapper(request, *args, **kwargs):
            events.append("decorator")
            seen_auth.append(getattr(request, "auth", None))
            return await func(request, *args, **kwargs)

        return wrapper

    return decorator


@pytest.mark.asyncio
async def test_async_auth_runs_before_view_decorator():
    events, seen_auth = [], []
    api = NinjaAPI(auth=CountingKeyAuth(events), urls_namespace="auth_order_6")
    api.add_decorator(recording_async_view_decorator(events, seen_auth), mode="view")

    @api.get("/thing")
    async def thing(request):
        events.append("view")
        return {"auth": request.auth}

    client = TestAsyncClient(api)
    response = await client.get("/thing", headers=GOOD)

    assert response.status_code == 200
    assert response.json() == {"auth": {"tenant": "acme"}}
    assert seen_auth == [{"tenant": "acme"}]
    assert events == ["auth", "decorator", "view"]


@pytest.mark.asyncio
async def test_async_unauthenticated_short_circuits_before_view_decorator():
    events, seen_auth = [], []
    api = NinjaAPI(auth=CountingKeyAuth(events), urls_namespace="auth_order_7")
    api.add_decorator(recording_async_view_decorator(events, seen_auth), mode="view")

    @api.get("/thing")
    async def thing(request):  # pragma: no cover
        events.append("view")
        return {}

    client = TestAsyncClient(api)
    response = await client.get("/thing")

    assert response.status_code == 401
    assert events == ["auth"]
    assert seen_auth == []
