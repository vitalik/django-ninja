from abc import ABC, abstractmethod
from typing import Any, Optional

from django.http import HttpRequest

from ninja.errors import ConfigError

__all__ = ["SecuritySchema", "AuthBase"]


class SecuritySchema(dict):
    def __init__(self, type: str, **kwargs: Any) -> None:
        super().__init__(type=type, **kwargs)


class AuthBase(ABC):
    def __init__(self) -> None:
        if not hasattr(self, "openapi_type"):
            raise ConfigError("If you extend AuthBase you need to define openapi_type")

        kwargs = {}
        for attr in dir(self):
            if attr.startswith("openapi_"):
                name = attr.replace("openapi_", "", 1)
                kwargs[name] = getattr(self, attr)
        self.openapi_security_schema = SecuritySchema(**kwargs)

    @abstractmethod
    def __call__(self, request: HttpRequest) -> Optional[Any]:
        pass  # pragma: no cover
