import traceback
from typing import TYPE_CHECKING, List, Dict, Any
from django.conf import settings
from django.http import HttpRequest, HttpResponse, Http404


if TYPE_CHECKING:
    from ninja import NinjaAPI  # pragma: no cover


class ConfigError(Exception):
    pass


class ValidationError(Exception):
    def __init__(self, errors: List[Dict[str, Any]]) -> None:
        super().__init__()
        self.errors = errors


class HttpError(Exception):
    def __init__(self, status_code: int, message: str) -> None:
        self.status_code = status_code
        super().__init__(message)


def set_default_exc_handlers(api: "NinjaAPI"):
    api.add_exception_handler(Exception, _default_exception)
    api.add_exception_handler(Http404, _default_404)
    api.add_exception_handler(HttpError, _default_http_error)
    api.add_exception_handler(ValidationError, _default_validation_error)


def _default_404(api: "NinjaAPI", request: HttpRequest, exc: Exception):
    return api.create_response(
        request, {"code": 404, "message": "Not Found"}, status=404
    )


def _default_http_error(api: "NinjaAPI", request: HttpRequest, exc: Exception):
    return api.create_response(
        request, {"code": exc.status_code, "message": str(exc)}, status=exc.status_code
    )


def _default_validation_error(api: "NinjaAPI", request: HttpRequest, exc: Exception):
    return api.create_response(request, {"detail": exc.errors}, status=422)


def _default_exception(api: "NinjaAPI", request: HttpRequest, exc: Exception):
    if not settings.DEBUG:
        raise exc  # let django deal with it

    tb = traceback.format_exc()
    return HttpResponse(tb, status=500, content_type="text/plain")
