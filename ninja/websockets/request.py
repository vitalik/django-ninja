import io
from importlib import import_module
from typing import Any, Awaitable, Callable

from django.http import HttpRequest

from ninja.websockets.types import Scope

__all__ = ["build_handshake_request"]

_HTTP_SCHEMES = {"ws": "http", "wss": "https", "http": "http", "https": "https"}


def build_handshake_request(scope: Scope) -> HttpRequest:
    """
    A read-only Django request built from a websocket handshake scope
    (method GET, no body). Auth callbacks and Path/Query/Header/Cookie params
    receive it, so existing ninja security classes work unchanged.
    """
    from django.core.handlers.asgi import ASGIRequest

    http_scope = dict(scope)
    http_scope["method"] = "GET"
    http_scope["scheme"] = _HTTP_SCHEMES.get(str(scope.get("scheme")), "http")
    request = ASGIRequest(http_scope, io.BytesIO(b""))
    _attach_session_and_user(request)
    return request


def _attach_session_and_user(request: HttpRequest) -> None:
    """
    Django middlewares do not run for websockets: emulate what
    SessionMiddleware/AuthenticationMiddleware add to the request
    (``session``, ``user`` and ``auser()``) so that session based auth
    (e.g. ninja.security.django_auth) keeps working. All of them are lazy,
    the database is only hit when they are used.
    """
    from django.apps import apps
    from django.conf import settings

    if not apps.is_installed("django.contrib.sessions"):
        return

    engine = import_module(settings.SESSION_ENGINE)
    session_key = request.COOKIES.get(settings.SESSION_COOKIE_NAME)
    request.session = engine.SessionStore(session_key)

    if apps.is_installed("django.contrib.auth"):
        from django.contrib.auth import get_user
        from django.utils.functional import SimpleLazyObject

        request.user = SimpleLazyObject(lambda: get_user(request))  # type: ignore
        request.auser = _make_auser(request)


def _make_auser(request: HttpRequest) -> Callable[[], Awaitable[Any]]:
    """``await request.auser()``, like Django's AuthenticationMiddleware (5.0+)."""
    try:
        from django.contrib.auth import aget_user
    except ImportError:  # pragma: no cover - Django < 5.0
        from asgiref.sync import sync_to_async
        from django.contrib.auth import get_user

        aget_user = sync_to_async(get_user)

    async def auser() -> Any:
        if not hasattr(request, "_acached_user"):
            request._acached_user = await aget_user(request)  # type: ignore
        return request._acached_user  # type: ignore

    return auser
