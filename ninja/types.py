from typing import Any, Callable, Dict, Type, TypeVar

from pydantic import BaseModel

__all__ = ["DictStrAny", "TCallable", "TSchemaClass"]

DictStrAny = Dict[str, Any]

TCallable = TypeVar("TCallable", bound=Callable[..., Any])

TSchemaClass = TypeVar("TSchemaClass", bound=Type[BaseModel])


# unfortunately this doesn't work yet, see
# https://github.com/python/mypy/issues/3924
# Decorator = Callable[[TCallable], TCallable]
