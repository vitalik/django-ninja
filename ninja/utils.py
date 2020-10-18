from typing import Callable
from django.http import HttpRequest
from django.middleware.csrf import CsrfViewMiddleware


def normalize_path(path: str) -> str:
    while "//" in path:
        path = path.replace("//", "/")
    return path


def check_csrf(request: HttpRequest, callback: Callable):
    mware = CsrfViewMiddleware(lambda: None)
    request.csrf_processing_done = False
    return mware.process_view(request, callback, [], {})
