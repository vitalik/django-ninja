import asyncio
import inspect
import re
import sys
from typing import Any, Callable, ForwardRef, List, Set, cast

from django.urls import register_converter
from django.urls.converters import UUIDConverter

if sys.version_info < (3, 9):  # pragma: nocover

    def evaluate_forwardref(type_: ForwardRef, globalns: Any, localns: Any) -> Any:
        return type_._evaluate(globalns, localns)

else:

    def evaluate_forwardref(type_: ForwardRef, globalns: Any, localns: Any) -> Any:
        # Even though it is the right signature for python 3.9, mypy complains with
        # `error: Too many arguments for "_evaluate" of "ForwardRef"` hence the cast...
        return cast(Any, type_)._evaluate(globalns, localns, set())


from ninja.types import DictStrAny

__all__ = [
    "get_typed_signature",
    "get_typed_annotation",
    "make_forwardref",
    "get_path_param_names",
    "is_async",
]


def get_typed_signature(call: Callable) -> inspect.Signature:
    "Finds call signature and resolves all forwardrefs"
    signature = inspect.signature(call)
    globalns = getattr(call, "__globals__", {})
    typed_params = [
        inspect.Parameter(
            name=param.name,
            kind=param.kind,
            default=param.default,
            annotation=get_typed_annotation(param, globalns),
        )
        for param in signature.parameters.values()
    ]
    typed_signature = inspect.Signature(typed_params)
    return typed_signature


def get_typed_annotation(param: inspect.Parameter, globalns: DictStrAny) -> Any:
    annotation = param.annotation
    if isinstance(annotation, str):
        annotation = make_forwardref(annotation, globalns)
    return annotation


def make_forwardref(annotation: str, globalns: DictStrAny) -> Any:
    forward_ref = ForwardRef(annotation)
    return evaluate_forwardref(forward_ref, globalns, globalns)


def get_path_param_names(path: str) -> Set[str]:
    """turns path string like /foo/{var}/path/{int:another}/end to set {'var', 'another'}"""
    return {item.strip("{}").split(":")[-1] for item in re.findall("{[^}]*}", path)}


def is_async(callable: Callable) -> bool:
    return asyncio.iscoroutinefunction(callable)


def has_kwargs(func: Callable) -> bool:
    for param in inspect.signature(func).parameters.values():
        if param.kind == param.VAR_KEYWORD:
            return True
    return False


def get_args_names(func: Callable) -> List[str]:
    "returns list of function argument names"
    return list(inspect.signature(func).parameters.keys())


class NinjaUUIDConverter:
    """Return a path converted UUID as a str instead of the standard UUID"""

    regex = UUIDConverter.regex

    def to_python(self, value: str) -> str:
        return value

    def to_url(self, value: Any) -> str:
        return str(value)


register_converter(NinjaUUIDConverter, "uuid")
