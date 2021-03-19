from typing import Callable, Optional

from django.http import HttpRequest, HttpResponseForbidden
from django.middleware.csrf import CsrfViewMiddleware

__all__ = ["normalize_path", "check_csrf"]


def normalize_path(path: str) -> str:
    while "//" in path:
        path = path.replace("//", "/")
    return path


def check_csrf(
    request: HttpRequest, callback: Callable
) -> Optional[HttpResponseForbidden]:
    mware = CsrfViewMiddleware(lambda: None)  # type: ignore
    request.csrf_processing_done = False  # type: ignore
    mware.process_request(request)
    return mware.process_view(request, callback, (), {})
