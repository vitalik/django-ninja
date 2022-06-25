from typing import Any, Optional

from django.conf import settings
from django.http import HttpRequest

from ninja.security.apikey import APIKeyCookie

__all__ = ["SessionAuth", "SessionAuthSuperUser"]


class SessionAuth(APIKeyCookie):
    "Reusing Django session authentication"
    param_name: str = settings.SESSION_COOKIE_NAME

    def authenticate(self, request: HttpRequest, key: Optional[str]) -> Optional[Any]:
        if request.user.is_authenticated:
            return request.user

        return None


class SessionAuthSuperUser(APIKeyCookie):
    "Reusing Django session authentication & verify that the user is a super user"
    param_name: str = settings.SESSION_COOKIE_NAME

    def authenticate(self, request: HttpRequest, key: Optional[str]) -> Optional[Any]:
        is_superuser = getattr(request.user, "is_superuser", None)
        if request.user.is_authenticated and is_superuser:
            return request.user

        return None
