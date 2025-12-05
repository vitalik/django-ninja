from functools import partial
from typing import Any, Callable, Tuple

from typing_extensions import Literal

from ninja.operation import Operation
from ninja.types import TCallable
from ninja.utils import contribute_operation_callback

# Type for decorator modes
DecoratorMode = Literal["operation", "view"]

# Since @api.method decorator is applied to function
# that is not always returns a HttpResponse object
# there is no way to apply some standard decorators form
# django stdlib or public plugins
#
# @decorate_view allows to apply any view decorator to Ninja api operation
#
# @api.get("/some")
# @decorate_view(cache_page(60 * 15)) # <-------
# def some(request):
#     ...
#


def decorate_view(
    *decorators: Callable[..., Any],
    mode: DecoratorMode = "view",  # 'view' mode is used by default for backward compatibility
) -> Callable[[TCallable], TCallable]:
    def outer_wrapper(op_func: TCallable) -> TCallable:
        if hasattr(op_func, "_ninja_operation"):
            # Means user used decorate_view on top of @api.method
            apply_decorators(decorators, mode, op_func._ninja_operation)  # type: ignore
        else:
            # Means user used decorate_view after(bottom) of @api.method
            contribute_operation_callback(
                op_func, partial(apply_decorators, decorators, mode)
            )

        return op_func

    return outer_wrapper


def apply_decorators(
    decorators: Tuple[Callable[..., Any]], mode: DecoratorMode, operation: Operation
) -> None:
    for deco in decorators:
        apply_decorator(deco, mode, operation)


def apply_decorator(
    decorator: Callable[..., Any], mode: DecoratorMode, operation: Operation
) -> None:
    if mode == "view":
        operation.run = decorator(operation.run)  # type: ignore
    elif mode == "operation":
        operation.view_func = decorator(operation.view_func)
    else:
        raise ValueError(f"Invalid decorator mode: {mode}")  # pragma: no cover
