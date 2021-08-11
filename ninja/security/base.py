from abc import ABC, abstractmethod
from typing import Any, Optional

from django.http import HttpRequest

from ninja.errors import ConfigError

__all__ = ["SecuritySchema", "AuthBase"]


class SecuritySchema(dict):
    def __init__(self, type: str, **kwargs: Any) -> None:
        super().__init__(type=type, **kwargs)


class AuthBase(ABC):
    def __init__(
        self,
        and_neighbour: Optional["AuthBase"] = None,
        or_neighbour: Optional["AuthBase"] = None,
    ) -> None:
        if not hasattr(self, "openapi_type"):
            raise ConfigError("If you extend AuthBase you need to define openapi_type")

        kwargs = {}
        for attr in dir(self):
            if attr.startswith("openapi_"):
                name = attr.replace("openapi_", "", 1)
                kwargs[name] = getattr(self, attr)
        self.openapi_security_schema = SecuritySchema(**kwargs)

        self.and_neighbour = and_neighbour
        self.or_neighbour = or_neighbour

    def __call__(self, request: HttpRequest) -> Optional[Any]:
        left_operand = self.callable(request)
        if self.and_neighbour:
            right_operand = self.and_neighbour(request)
            return left_operand if left_operand and right_operand else None
        if self.or_neighbour:
            right_operand = self.or_neighbour(request)
            return left_operand if left_operand else right_operand
        return left_operand

    @abstractmethod
    def callable(self, request: HttpRequest) -> Optional[Any]:
        pass  # pragma: no cover

    def __and__(self, another: "AuthBase") -> Any:
        another.and_neighbour = self.and_neighbour
        return type(self)(and_neighbour=another)

    def __or__(self, another: "AuthBase") -> Any:
        another.or_neighbour = self.or_neighbour
        return type(self)(or_neighbour=another)
