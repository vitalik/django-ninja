import logging
from abc import ABC, abstractmethod
from base64 import b64decode
from typing import Any, Optional, Tuple
from urllib.parse import unquote

from django.conf import settings
from django.http import HttpRequest

from ninja.compatibility import get_headers
from ninja.security.base import AuthBase

__all__ = ["HttpAuthBase", "HttpBearer", "DecodeError", "HttpBasicAuth"]


logger = logging.getLogger("django")


class HttpAuthBase(AuthBase, ABC):
    openapi_type: str = "http"


class HttpBearer(HttpAuthBase, ABC):
    openapi_scheme: str = "bearer"
    header: str = "Authorization"

    def __call__(self, request: HttpRequest) -> Optional[Any]:
        headers = get_headers(request)
        auth_value = headers.get(self.header)
        if not auth_value:
            return None
        parts = auth_value.split(" ")

        if parts[0].lower() != self.openapi_scheme:
            if settings.DEBUG:
                logger.error(f"Unexpected auth - '{auth_value}'")
            return None
        token = " ".join(parts[1:])
        return self.authenticate(request, token)

    @abstractmethod
    def authenticate(self, request: HttpRequest, token: str) -> Optional[Any]:
        pass  # pragma: no cover


class DecodeError(Exception):
    pass


class HttpBasicAuth(HttpAuthBase, ABC):  # TODO: maybe HttpBasicAuthBase
    openapi_scheme = "basic"
    header = "Authorization"

    def __call__(self, request: HttpRequest) -> Optional[Any]:
        headers = get_headers(request)
        auth_value = headers.get(self.header)
        if not auth_value:
            return None

        try:
            username, password = self.decode_authorization(auth_value)
        except DecodeError as e:
            if settings.DEBUG:
                logger.exception(e)
            return None
        return self.authenticate(request, username, password)

    @abstractmethod
    def authenticate(
        self, request: HttpRequest, username: str, password: str
    ) -> Optional[Any]:
        pass  # pragma: no cover

    def decode_authorization(self, value: str) -> Tuple[str, str]:
        parts = value.split(" ")
        if len(parts) == 1:
            user_pass_encoded = parts[0]
        elif len(parts) == 2 and parts[0].lower() == "basic":
            user_pass_encoded = parts[1]
        else:
            raise DecodeError("Invalid Authorization header")

        try:
            username, password = b64decode(user_pass_encoded).decode().split(":", 1)
            return unquote(username), unquote(password)
        except Exception as e:  # dear contributors please do not change to valueerror - here can be multiple exceptions
            raise DecodeError("Invalid Authorization header") from e
