import functools
from typing import Any

from pydantic import TypeAdapter

__all__ = ["type_adapter"]


def type_adapter(tp: Any) -> TypeAdapter:
    """A (cached when possible) pydantic TypeAdapter for any type."""
    try:
        return _cached_type_adapter(tp)
    except TypeError:  # unhashable type (e.g. Annotated with unhashable metadata)
        return TypeAdapter(tp)


@functools.lru_cache(maxsize=None)
def _cached_type_adapter(tp: Any) -> TypeAdapter:
    return TypeAdapter(tp)
