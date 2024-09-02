from abc import ABC, abstractmethod
from typing import Generic, List, TypeVar

from .schema import Schema

T = TypeVar("T")


class OrderingBaseSchema(Schema, ABC, Generic[T]):
    order_by: List[str] = []

    class Config:
        allowed_fields = "__all__"

    @abstractmethod
    def sort(self, elements: T) -> T:
        raise NotImplementedError
