from abc import ABC, abstractmethod
from typing import Any, Optional

from django.http import HttpRequest

from ninja.compatibility.request import get_headers
from ninja.security.base import AuthBase

__all__ = ["APIKeyBase", "APIKeyQuery", "APIKeyCookie", "APIKeyHeader"]


class APIKeyBase(AuthBase, ABC):
    openapi_type: str = "apiKey"
    param_name: str = "key"

    def __init__(self) -> None:
        self.openapi_name = self.param_name
        super().__init__()

    def __call__(self, request: HttpRequest) -> Optional[Any]:
        key = self._get_key(request)
        return self.authenticate(request, key)

    @abstractmethod
    def _get_key(self, request: HttpRequest) -> Optional[str]:
        pass  # pragma: no cover

    @abstractmethod
    def authenticate(self, request: HttpRequest, key: Optional[str]) -> Optional[Any]:
        pass  # pragma: no cover


class APIKeyQuery(APIKeyBase, ABC):
    openapi_in: str = "query"

    def _get_key(self, request: HttpRequest) -> Optional[str]:
        return request.GET.get(self.param_name)


class APIKeyCookie(APIKeyBase, ABC):
    openapi_in: str = "cookie"

    def _get_key(self, request: HttpRequest) -> Optional[str]:
        return request.COOKIES.get(self.param_name)


class APIKeyHeader(APIKeyBase, ABC):
    openapi_in: str = "header"

    def _get_key(self, request: HttpRequest) -> Optional[str]:
        headers = get_headers(request)
        return headers.get(self.param_name)
