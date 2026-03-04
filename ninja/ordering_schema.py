from typing import Any, Generic, List, TypeVar

from django.db.models import QuerySet
from pydantic import ConfigDict, Field, field_validator
from pydantic.fields import FieldInfo

from .schema import Schema

QS = TypeVar("QS", bound=QuerySet)


class OrderingBaseSchema(Schema, Generic[QS]):
    model_config = ConfigDict(from_attributes=True)

    order_by: List[str] = Field(default_factory=list)

    class Meta:
        allowed_fields = "__all__"
        ordering_query_param = "order_by"

    @classmethod
    def __pydantic_init_subclass__(cls, **kwargs: Any) -> None:
        super().__pydantic_init_subclass__(**kwargs)

        ordering_query_param: str = getattr(
            cls.Meta, "ordering_query_param", "order_by"
        )
        order_by_field: FieldInfo = cls.model_fields.get("order_by")

        if ordering_query_param == "order_by":
            order_by_field.alias = None
            order_by_field.validation_alias = None
            order_by_field.serialization_alias = None
        else:
            order_by_field.alias = ordering_query_param
            order_by_field.validation_alias = ordering_query_param
            order_by_field.serialization_alias = ordering_query_param

        cls.model_rebuild(force=True)

    @field_validator("order_by")
    @classmethod
    def validate_order_by_field(cls, value: List[str]) -> List[str]:
        allowed_fields = cls.Meta.allowed_fields
        if value and allowed_fields != "__all__":
            allowed_fields_set = set(allowed_fields)
            for order_field in value:
                field_name = order_field.lstrip("-")
                if field_name not in allowed_fields_set:
                    raise ValueError(f"Ordering by {field_name} is not allowed")

        return value

    @property
    def parsed_order_by(self) -> List[str]:
        parsed_order_by: List[str] = []
        if isinstance(self.Meta.allowed_fields, dict):
            for field in self.order_by:
                is_decreasing = field.startswith("-")
                field_name = field.lstrip("-")
                new_field_name = self.Meta.allowed_fields.get(field_name)
                parsed_order_by.append(
                    f"-{new_field_name}" if is_decreasing else new_field_name
                )
            return parsed_order_by
        return self.order_by

    def sort(self, queryset: QS) -> QS:
        raise NotImplementedError


class OrderingSchema(OrderingBaseSchema):
    def sort(self, queryset: QS) -> QS:
        ordering_fields = self.parsed_order_by
        if not ordering_fields:
            return queryset
        return queryset.order_by(*ordering_fields)
