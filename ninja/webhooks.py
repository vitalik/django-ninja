import copy
from typing import Any, Dict, List, Optional, Type

from pydantic import BaseModel

from ninja.errors import ConfigError

__all__ = ["Webhook"]


class Webhook:
    """
    Describes an outgoing request (webhook) that your API sends to other services.

    Webhooks are documentation-only: they are rendered in the OpenAPI ``webhooks``
    section, but Django Ninja does not send them for you.
    """

    def __init__(
        self,
        name: str,
        schema: Type[BaseModel],
        *,
        method: str = "POST",
        summary: Optional[str] = None,
        description: Optional[str] = None,
        tags: Optional[List[str]] = None,
        operation_id: Optional[str] = None,
        deprecated: Optional[bool] = None,
        include_in_schema: bool = True,
        openapi_extra: Optional[Dict[str, Any]] = None,
    ) -> None:
        if not (isinstance(schema, type) and issubclass(schema, BaseModel)):
            raise ConfigError(
                f'Webhook "{name}" payload must be a Schema (pydantic model) '
                f"class, got {schema!r}"
            )
        self.name = name
        self.schema = schema
        self.method = method.lower()
        self.summary = summary or _title_from_class_name(schema.__name__)
        self.description = description
        self.tags = tags
        self.operation_id = operation_id
        self.deprecated = deprecated
        self.include_in_schema = include_in_schema
        self.openapi_extra = openapi_extra

    def clone(self, **changes: Any) -> "Webhook":
        cloned = copy.copy(self)
        cloned.__dict__.update(changes)
        return cloned


def _title_from_class_name(name: str) -> str:
    # "OrderPaid" -> "Order Paid"
    words: List[str] = []
    for i, char in enumerate(name):
        if (
            char.isupper()
            and i > 0
            and (
                not name[i - 1].isupper()
                or (i + 1 < len(name) and name[i + 1].islower())
            )
        ):
            words.append(" ")
        words.append(char)
    return "".join(words)
