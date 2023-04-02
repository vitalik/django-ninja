import inspect
from typing import Callable, Optional

from django.conf import settings
from django.http import HttpRequest, HttpResponseForbidden
from django.middleware.csrf import CsrfViewMiddleware

__all__ = ["check_csrf", "is_debug_server", "normalize_path"]


def replace_path_param_notation(path: str) -> str:
    return path.replace("{", "<").replace("}", ">")


def normalize_path(path: str) -> str:
    while "//" in path:
        path = path.replace("//", "/")
    return path


def check_csrf(
    request: HttpRequest, callback: Callable
) -> Optional[HttpResponseForbidden]:
    mware = CsrfViewMiddleware(lambda x: HttpResponseForbidden())  # pragma: no cover
    request.csrf_processing_done = False  # type: ignore
    mware.process_request(request)
    return mware.process_view(request, callback, (), {})


def is_debug_server() -> bool:
    """Check if running under the Django Debug Server"""
    return settings.DEBUG and any(
        s.filename.endswith("runserver.py") and s.function == "run"
        for s in inspect.stack(0)[1:]
    )


def is_async_callable(f: Callable) -> bool:
    return inspect.iscoroutinefunction(f) or inspect.iscoroutinefunction(
        getattr(f, "__call__", None)
    )
