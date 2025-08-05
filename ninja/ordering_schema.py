from typing import Any, List, TypeVar

from django.db.models import QuerySet
from pydantic import field_validator

from .schema import Schema

QS = TypeVar("QS", bound=QuerySet)


class OrderingBaseSchema(Schema):
    order_by: List[str] = []

    class Config(Schema.Config):
        allowed_fields = "__all__"

    @field_validator("order_by")
    @classmethod
    def validate_order_by_field(cls, value: List[str]) -> List[str]:
        allowed_fields = cls.Config.allowed_fields
        if value and allowed_fields != "__all__":
            allowed_fields_set = set(allowed_fields)
            for order_field in value:
                field_name = order_field.lstrip("-")
                if field_name not in allowed_fields_set:
                    raise ValueError(f"Ordering by {field_name} is not allowed")

        return value

    def sort(self, elements: Any) -> Any:
        raise NotImplementedError


class OrderingSchema(OrderingBaseSchema):
    def sort(self, queryset: QS) -> QS:
        if not self.order_by:
            return queryset
        return queryset.order_by(*self.order_by)
