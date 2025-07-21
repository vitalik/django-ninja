import asyncio
import inspect
import re
from typing import Any, Callable, ForwardRef, List, Set

from django.urls import register_converter
from django.urls.converters import UUIDConverter
from pydantic._internal._typing_extra import eval_type_lenient as evaluate_forwardref

from ninja.types import DictStrAny

__all__ = [
    "get_typed_signature",
    "get_typed_annotation",
    "make_forwardref",
    "get_path_param_names",
    "is_async",
]


def get_typed_signature(call: Callable[..., Any]) -> inspect.Signature:
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
    # NOTE: in future versions of pydantic, the import may be changed to:
    # from pydantic._internal._typing_extra import try_eval_type
    # usage:
    # result, _ = try_eval_type(forward_ref, globalns, globalns)
    forward_ref = ForwardRef(annotation)
    return evaluate_forwardref(forward_ref, globalns, globalns)


def get_path_param_names(path: str) -> Set[str]:
    """turns path string like /foo/{var}/path/{int:another}/end to set {'var', 'another'}"""
    return {item.strip("{}").split(":")[-1] for item in re.findall("{[^}]*}", path)}


def is_async(callable: Callable[..., Any]) -> bool:
    return asyncio.iscoroutinefunction(callable)


def has_kwargs(func: Callable[..., Any]) -> bool:
    for param in inspect.signature(func).parameters.values():
        if param.kind == param.VAR_KEYWORD:
            return True
    return False


def get_args_names(func: Callable[..., Any]) -> List[str]:
    "returns list of function argument names"
    return list(inspect.signature(func).parameters.keys())


class UUIDStrConverter(UUIDConverter):
    """Return a path converted UUID as a str instead of the standard UUID"""

    def to_python(self, value: str) -> str:  # type: ignore
        return value  # return string value instead of UUID


register_converter(UUIDStrConverter, "uuidstr")
