from ninja.security.apikey import APIKeyCookie, APIKeyHeader, APIKeyQuery
from ninja.security.http import HttpBasicAuth, HttpBearer
from ninja.security.permission import BasePermission
from ninja.security.session import SessionAuth

__all__ = [
    "APIKeyCookie",
    "APIKeyHeader",
    "APIKeyQuery",
    "HttpBasicAuth",
    "HttpBearer",
    "SessionAuth",
    "BasePermission",
    "django_auth",
]

django_auth = SessionAuth()
