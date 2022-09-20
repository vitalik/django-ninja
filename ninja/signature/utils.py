import asyncio
import inspect
import re
from typing import Any, Callable, Set

from django.urls import register_converter
from django.urls.converters import UUIDConverter
from pydantic.typing import ForwardRef, evaluate_forwardref  # type: ignore

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


class NinjaUUIDConverter:
    """Return a path converted UUID as a str instead of the standard UUID"""

    regex = UUIDConverter.regex

    def to_python(self, value: str) -> str:
        return value

    def to_url(self, value: Any) -> str:
        return str(value)


register_converter(NinjaUUIDConverter, "uuid")
