import logging
import traceback
from functools import partial
from typing import TYPE_CHECKING, List

from django.conf import settings
from django.http import Http404, HttpRequest, HttpResponse

from ninja.types import DictStrAny

if TYPE_CHECKING:
    from ninja import NinjaAPI  # pragma: no cover

__all__ = [
    "ConfigError",
    "AuthenticationError",
    "ValidationError",
    "HttpError",
    "set_default_exc_handlers",
]


logger = logging.getLogger("django")


class ConfigError(Exception):
    pass


class AuthenticationError(Exception):
    pass


class ValidationError(Exception):
    """
    This exception raised when operation params do not validate
    Note: this is not the same as pydantic.ValidationError
    the errors attribute as well holds the location of the error(body, form, query, etc.)
    """

    def __init__(self, errors: List[DictStrAny]) -> None:
        super().__init__()
        self.errors = errors


class HttpError(Exception):
    def __init__(self, status_code: int, message: str) -> None:
        self.status_code = status_code
        super().__init__(message)


def set_default_exc_handlers(api: "NinjaAPI") -> None:
    api.add_exception_handler(
        Exception,
        partial(_default_exception, api=api),
    )
    api.add_exception_handler(
        Http404,
        partial(_default_404, api=api),
    )
    api.add_exception_handler(
        HttpError,
        partial(_default_http_error, api=api),
    )
    api.add_exception_handler(
        ValidationError,
        partial(_default_validation_error, api=api),
    )
    api.add_exception_handler(
        AuthenticationError,
        partial(_default_authentication_error, api=api),
    )


def _default_404(request: HttpRequest, exc: Exception, api: "NinjaAPI") -> HttpResponse:
    msg = "Not Found"
    if settings.DEBUG:
        msg += f": {exc}"
    return api.create_response(request, {"detail": msg}, status=404)


def _default_http_error(
    request: HttpRequest, exc: HttpError, api: "NinjaAPI"
) -> HttpResponse:
    return api.create_response(request, {"detail": str(exc)}, status=exc.status_code)


def _default_validation_error(
    request: HttpRequest, exc: ValidationError, api: "NinjaAPI"
) -> HttpResponse:
    return api.create_response(request, {"detail": exc.errors}, status=422)


def _default_authentication_error(
    request: HttpRequest, exc: AuthenticationError, api: "NinjaAPI"
) -> HttpResponse:
    return api.create_response(request, {"detail": "Unauthorized"}, status=401)


def _default_exception(
    request: HttpRequest, exc: Exception, api: "NinjaAPI"
) -> HttpResponse:
    if not settings.DEBUG:
        raise exc  # let django deal with it

    logger.exception(exc)
    tb = traceback.format_exc()
    return HttpResponse(tb, status=500, content_type="text/plain")
