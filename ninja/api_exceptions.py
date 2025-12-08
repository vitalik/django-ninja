from typing import Any, Callable, Dict, List, Optional, Type, TypeVar, Union

from django.http import HttpRequest, HttpResponse
from ninja.errors import ValidationError, ValidationErrorContext
_E = TypeVar("_E", bound=Exception)
Exc = Union[_E, Type[_E]]
ExcHandler = Callable[[HttpRequest, Exc[_E]], HttpResponse]

class ExceptionRegistry:
    def __init__(self):
        self._handlers: Dict[Exc, ExcHandler] = {}

    def add_handler(self, exc_class: Type[_E], handler: ExcHandler[_E]) -> None:
        assert issubclass(exc_class, Exception)
        self._handlers[exc_class] = handler

    def lookup(self, exc: Exc[_E]) -> Optional[ExcHandler[_E]]:
        for cls in type(exc).__mro__:
            if cls in self._handlers:
                return self._handlers[cls]
        return None

    def validation_error_from_contexts(
        self, error_contexts: List[ValidationErrorContext]
    ) -> ValidationError:
        errors: List[Dict[str, Any]] = []
        for context in error_contexts:
            model = context.model
            e = context.pydantic_validation_error
            for i in e.errors(include_url=False):
                i["loc"] = (
                    model.__ninja_param_source__,
                ) + model.__ninja_flatten_map_reverse__.get(i["loc"], i["loc"])
                # removing pydantic hints
                del i["input"]  # type: ignore
                if (
                    "ctx" in i
                    and "error" in i["ctx"]
                    and isinstance(i["ctx"]["error"], Exception)
                ):
                    i["ctx"]["error"] = str(i["ctx"]["error"])
                errors.append(dict(i))
        return ValidationError(errors)
