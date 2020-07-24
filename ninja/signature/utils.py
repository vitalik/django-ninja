import re
import inspect
import asyncio
from typing import Callable, Dict, Any, Set
from pydantic.typing import ForwardRef, evaluate_forwardref


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


def get_typed_annotation(param: inspect.Parameter, globalns: Dict[str, Any]) -> Any:
    annotation = param.annotation
    if isinstance(annotation, str):
        annotation = make_forwardref(annotation, globalns)
    return annotation


def make_forwardref(annotation: str, globalns: Dict[str, Any]):
    annotation = ForwardRef(annotation)
    annotation = evaluate_forwardref(annotation, globalns, globalns)
    return annotation


def get_path_param_names(path: str) -> Set[str]:
    "turns path string like /foo/{var}/path/{another}/end to set ['var', 'another']"
    return {item.strip("{}") for item in re.findall("{[^}]*}", path)}


def is_async(callable: Callable):
    return asyncio.iscoroutinefunction(callable)
