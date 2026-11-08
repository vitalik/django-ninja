from abc import ABC, abstractmethod
from typing import Any, Optional

from django.http import HttpRequest

from ninja.errors import HttpError
from ninja.security.base import AuthBase
from ninja.utils import check_csrf

__all__ = ["APIKeyBase", "APIKeyQuery", "APIKeyCookie", "APIKeyHeader"]


class APIKeyBase(AuthBase, ABC):
    openapi_type: str = "apiKey"
    param_name: str = "key"

    def __init__(self) -> None:
        self.openapi_name = self.param_name  # this sets the name of the security schema
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

    def __init__(self, csrf: bool = True) -> None:
        self.csrf = csrf
        super().__init__()

    def __call__(self, request: HttpRequest) -> Optional[Any]:
        # Skip CSRF check if the operation is marked as csrf_exempt
        if self.csrf and not getattr(request, "_ninja_csrf_exempt", False):
            error_response = check_csrf(request)
            if error_response:
                if self.param_name not in request.COOKIES:
                    # No auth cookie, so this scheme can't authenticate the
                    # request and there is no ambient credential to protect.
                    # Report "not authenticated" (without calling
                    # authenticate()) so the next authenticator in the list
                    # gets a chance, e.g. a Bearer token from a non-browser
                    # client.
                    return None
                raise HttpError(403, "CSRF check Failed")
        return super().__call__(request)

    def _get_key(self, request: HttpRequest) -> Optional[str]:
        return request.COOKIES.get(self.param_name)


class APIKeyHeader(APIKeyBase, ABC):
    openapi_in: str = "header"

    def _get_key(self, request: HttpRequest) -> Optional[str]:
        headers = request.headers
        return headers.get(self.param_name)
