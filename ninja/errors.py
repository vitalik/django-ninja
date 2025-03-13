import logging
import traceback
from functools import partial
from typing import TYPE_CHECKING, Generic, List, Optional, TypeVar

import pydantic
from django.conf import settings
from django.http import Http404, HttpRequest, HttpResponse

from ninja.types import DictStrAny

if TYPE_CHECKING:
    from ninja import NinjaAPI  # pragma: no cover
    from ninja.params.models import ParamModel  # pragma: no cover

__all__ = [
    "ConfigError",
    "AuthenticationError",
    "AuthorizationError",
    "ValidationError",
    "HttpError",
    "set_default_exc_handlers",
]


logger = logging.getLogger("django")


class ConfigError(Exception):
    pass


TModel = TypeVar("TModel", bound="ParamModel")


class ValidationErrorContext(Generic[TModel]):
    """
    The full context of a `pydantic.ValidationError`, including all information
    needed to produce a `ninja.errors.ValidationError`.
    """

    def __init__(
        self, pydantic_validation_error: pydantic.ValidationError, model: TModel
    ):
        self.pydantic_validation_error = pydantic_validation_error
        self.model = model


class ValidationError(Exception):
    """
    This exception raised when operation params do not validate
    Note: this is not the same as pydantic.ValidationError
    the errors attribute as well holds the location of the error(body, form, query, etc.)
    """

    def __init__(self, errors: List[DictStrAny]) -> None:
        self.errors = errors
        super().__init__(errors)


class HttpError(Exception):
    def __init__(self, status_code: int, message: str) -> None:
        self.status_code = status_code
        self.message = message
        super().__init__(status_code, message)

    def __str__(self) -> str:
        return self.message


class AuthenticationError(HttpError):
    def __init__(self, status_code: int = 401, message: str = "Unauthorized") -> None:
        super().__init__(status_code=status_code, message=message)


class AuthorizationError(HttpError):
    def __init__(self, status_code: int = 403, message: str = "Forbidden") -> None:
        super().__init__(status_code=status_code, message=message)


class Throttled(HttpError):
    def __init__(self, wait: Optional[int]) -> None:
        self.wait = wait
        super().__init__(status_code=429, message="Too many requests.")


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


def _default_exception(
    request: HttpRequest, exc: Exception, api: "NinjaAPI"
) -> HttpResponse:
    if not settings.DEBUG:
        raise exc  # let django deal with it

    logger.exception(exc)
    tb = traceback.format_exc()
    return HttpResponse(tb, status=500, content_type="text/plain")
