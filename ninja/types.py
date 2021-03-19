from typing import Any, Callable, Dict, TypeVar

__all__ = ["DictStrAny", "TCallable", "Decorator"]

DictStrAny = Dict[str, Any]

TCallable = TypeVar("TCallable", bound=Callable)
Decorator = Callable[[TCallable], TCallable]
