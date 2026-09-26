import copy
from typing import TYPE_CHECKING, Any, Dict, List, Optional, Type

from pydantic import BaseModel

from ninja.errors import ConfigError

if TYPE_CHECKING:
    from ninja import NinjaAPI  # pragma: no cover

__all__ = ["Webhook", "get_webhooks"]


class Webhook:
    """
    Describes an outgoing request (webhook) that your API sends to other services.

    Webhooks are documentation-only: they are rendered in the OpenAPI ``webhooks``
    section, but Django Ninja does not send them for you.
    """

    def __init__(
        self,
        schema: Type[BaseModel],
        name: Optional[str] = None,
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
                f"Webhook payload must be a Schema (pydantic model) class, got {schema!r}"
            )
        self.name = name or schema.__name__
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


def get_webhooks(api: "NinjaAPI") -> List[Webhook]:
    """
    All webhooks registered on the api and its mounted routers.
    Router tags are applied to webhooks that don't define their own.
    """
    registered: Dict[str, Webhook] = {}
    result: List[Webhook] = []
    for bound_router in api._get_bound_routers():
        for name, webhook in bound_router.template.webhooks.items():
            if name in registered:
                if registered[name] is webhook:
                    continue  # same router mounted more than once
                raise ConfigError(f'Webhook "{name}" is registered more than once')
            registered[name] = webhook
            if webhook.tags is None and bound_router.tags is not None:
                webhook = webhook.clone(tags=bound_router.tags)
            result.append(webhook)
    return result


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
