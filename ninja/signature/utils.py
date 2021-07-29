import asyncio
import inspect
import re
from typing import Any, Callable, Dict, Union
from uuid import UUID

from pydantic.typing import ForwardRef, evaluate_forwardref

from ninja.types import DictStrAny

__all__ = [
    "get_typed_signature",
    "get_typed_annotation",
    "make_forwardref",
    "get_path_param_names_types",
    "is_async",
]

django_default_path_converter_types = {
    "str": str,
    "int": int,
    "slug": str,
    "uuid": UUID,
    "path": str,
}


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


def get_path_param_names_types(path: str) -> Dict[str, Union[type, None]]:
    """turns path string like /foo/{var}/path/{int:another}/end to dict {'var': None, 'another': int}"""
    # ::TODO:: custom path converters
    # https://docs.djangoproject.com/en/3.2/topics/http/urls/#registering-custom-path-converters
    names_types = (
        ([None] + item.strip("{}").split(":"))[-1:-3:-1]
        for item in re.findall("{[^}]*}", path)
    )
    return {
        name: django_default_path_converter_types.get(type_)
        for name, type_ in names_types
    }


def is_async(callable: Callable) -> bool:
    return asyncio.iscoroutinefunction(callable)
