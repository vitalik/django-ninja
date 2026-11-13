import functools
from typing import Any

import pydantic
from pydantic import TypeAdapter

from ninja.errors import ValidationError, clean_pydantic_errors

__all__ = ["type_adapter", "validate_message"]


def type_adapter(tp: Any) -> TypeAdapter:
    """A (cached when possible) pydantic TypeAdapter for any type."""
    try:
        return _cached_type_adapter(tp)
    except TypeError:  # unhashable type (e.g. Annotated with unhashable metadata)
        return TypeAdapter(tp)


@functools.lru_cache(maxsize=None)
def _cached_type_adapter(tp: Any) -> TypeAdapter:
    return TypeAdapter(tp)


def validate_message(schema: Any, data: Any) -> Any:
    """
    Validate an incoming message. Failures raise ``ninja.errors.ValidationError``
    (JSON-safe errors, like HTTP 422 responses).
    """
    try:
        return type_adapter(schema).validate_python(data)
    except pydantic.ValidationError as e:
        raise ValidationError(clean_pydantic_errors(e)) from e
