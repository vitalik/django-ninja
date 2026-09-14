"""ATOMIC_REQUESTS support: transaction.non_atomic_requests on Ninja routes.

Django's ``BaseHandler.make_view_atomic`` reads the ``_non_atomic_requests``
marker (installed by ``django.db.transaction.non_atomic_requests``) from the
URL callback. django-ninja builds that callback in ``PathView.get_view()``, so
the marker has to be forwarded from the wrapped operation view functions.

See https://github.com/vitalik/django-ninja/issues/1767
"""

import pytest
from django.conf import settings
from django.core.handlers.base import BaseHandler
from django.db import connection, transaction
from django.test import Client
from django.urls import path

from ninja import NinjaAPI


@pytest.fixture
def atomic_requests():
    """Temporarily enable ATOMIC_REQUESTS for the default connection.

    ``make_view_atomic`` reads ``connections.settings``, which shares the same
    per-alias dict objects as ``connection.settings_dict``.
    """
    original = connection.settings_dict.get("ATOMIC_REQUESTS")
    connection.settings_dict["ATOMIC_REQUESTS"] = True
    try:
        yield
    finally:
        if original is None:
            connection.settings_dict.pop("ATOMIC_REQUESTS", None)
        else:
            connection.settings_dict["ATOMIC_REQUESTS"] = original


def _callback(api, path_str):
    normalized = path_str.lstrip("/")
    for pattern in api.urls[0]:
        if hasattr(pattern, "pattern") and normalized in str(pattern.pattern):
            return pattern.callback
    raise AssertionError(f"pattern not found: {path_str}")


# Routes + URLconf used by the end-to-end handler test below
api = NinjaAPI(urls_namespace="test-non-atomic")


@api.get("/plain")
def plain(request):
    return {"in_atomic_block": connection.in_atomic_block}


@api.get("/non_atomic")
@transaction.non_atomic_requests
def non_atomic(request):
    return {"in_atomic_block": connection.in_atomic_block}


urlpatterns = [path("api/", api.urls)]


def test_non_atomic_marker_forwarded_to_callback():
    inner = NinjaAPI(urls_namespace="test-non-atomic-forwarded")

    @inner.get("/non_atomic")
    @transaction.non_atomic_requests
    def non_atomic_view(request):
        return {"ok": True}

    @inner.get("/plain")
    def plain_view(request):
        return {"ok": True}

    non_atomic_callback = _callback(inner, "/non_atomic")
    plain_callback = _callback(inner, "/plain")

    assert non_atomic_callback._non_atomic_requests == {"default"}
    assert not hasattr(plain_callback, "_non_atomic_requests")


def test_async_non_atomic_marker_forwarded_to_callback(atomic_requests):
    inner = NinjaAPI(urls_namespace="test-non-atomic-async")

    @inner.get("/non_atomic")
    @transaction.non_atomic_requests
    async def non_atomic_view(request):
        return {"ok": True}

    callback = _callback(inner, "/non_atomic")
    assert callback._non_atomic_requests == {"default"}
    # Django must not wrap an async view when the marker is present
    # (otherwise ATOMIC_REQUESTS raises RuntimeError for async views).
    assert BaseHandler().make_view_atomic(callback) is callback


def test_make_view_atomic_wraps_only_unmarked_routes(atomic_requests):
    inner = NinjaAPI(urls_namespace="test-non-atomic-wrap")

    @inner.get("/non_atomic")
    @transaction.non_atomic_requests
    def non_atomic_view(request):
        return {"ok": True}

    @inner.get("/plain")
    def plain_view(request):
        return {"ok": True}

    handler = BaseHandler()
    non_atomic_callback = _callback(inner, "/non_atomic")
    plain_callback = _callback(inner, "/plain")

    assert handler.make_view_atomic(non_atomic_callback) is non_atomic_callback
    assert handler.make_view_atomic(plain_callback) is not plain_callback


def test_non_atomic_for_other_database_alias(atomic_requests):
    inner = NinjaAPI(urls_namespace="test-non-atomic-other-alias")

    @inner.get("/other")
    @transaction.non_atomic_requests(using="other")
    def other_view(request):
        return {"ok": True}

    callback = _callback(inner, "/other")
    assert callback._non_atomic_requests == {"other"}
    # The default alias is still wrapped: "other" is NOT in the marker set.
    assert BaseHandler().make_view_atomic(callback) is not callback


def test_all_operations_non_atomic_forwarded():
    inner = NinjaAPI(urls_namespace="test-non-atomic-all")

    @inner.get("/item")
    @transaction.non_atomic_requests
    def get_item(request):
        return {"ok": True}

    @inner.post("/item")
    @transaction.non_atomic_requests
    def create_item(request):
        return {"ok": True}

    callback = _callback(inner, "/item")
    assert callback._non_atomic_requests == {"default"}


def test_mixed_operations_stay_atomic():
    inner = NinjaAPI(urls_namespace="test-non-atomic-mixed")

    @inner.get("/item")
    @transaction.non_atomic_requests
    def get_item(request):
        return {"ok": True}

    @inner.post("/item")
    def create_item(request):
        return {"ok": True}

    callback = _callback(inner, "/item")
    # The path is shared by marked and unmarked operations -> the conservative
    # choice is to keep the whole path atomic.
    assert not hasattr(callback, "_non_atomic_requests")


@pytest.mark.django_db(transaction=True)
def test_non_atomic_requests_honored_by_django_handler(atomic_requests, monkeypatch):
    monkeypatch.setattr(settings, "ROOT_URLCONF", __name__)
    client = Client()

    plain_response = client.get("/api/plain")
    non_atomic_response = client.get("/api/non_atomic")

    assert plain_response.json() == {"in_atomic_block": True}
    assert non_atomic_response.json() == {"in_atomic_block": False}
