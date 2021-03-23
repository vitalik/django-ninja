from typing import Any, Optional

from django.conf import settings
from django.http import HttpRequest

from ninja.security.apikey import APIKeyCookie

__all__ = ["SessionAuth"]


class SessionAuth(APIKeyCookie):
    "Reusing Django session authentication"
    param_name: str = settings.SESSION_COOKIE_NAME

    def authenticate(self, request: HttpRequest, key: Optional[str]) -> Optional[Any]:
        if request.user.is_authenticated:
            return request.user

        return None
