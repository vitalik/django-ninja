from typing import Any, Callable, TypeVar

from pydantic import BaseModel

__all__ = ["DictStrAny", "TCallable", "TSchemaClass"]

DictStrAny = dict[str, Any]

TCallable = TypeVar("TCallable", bound=Callable[..., Any])

TSchemaClass = TypeVar("TSchemaClass", bound=type[BaseModel])


# unfortunately this doesn't work yet, see
# https://github.com/python/mypy/issues/3924
# Decorator = Callable[[TCallable], TCallable]
