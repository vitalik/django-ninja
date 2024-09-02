from abc import ABC, abstractmethod
from typing import Generic, List, TypeVar

from pydantic import ValidationError, field_validator

from .schema import Schema

T = TypeVar("T")


class OrderingBaseSchema(Schema, ABC, Generic[T]):
    order_by: List[str] = []

    class Config:
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
                    raise ValidationError(f"Ordering by {field_name} is not allowed")

        return value

    @abstractmethod
    def sort(self, elements: T) -> T:
        raise NotImplementedError
