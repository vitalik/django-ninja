from ninja.security.apikey import APIKeyCookie, APIKeyHeader, APIKeyQuery
from ninja.security.http import HttpBasicAuth, HttpBearer
from ninja.security.session import SessionAuth

__all__ = [
    "APIKeyCookie",
    "APIKeyHeader",
    "APIKeyQuery",
    "HttpBasicAuth",
    "HttpBearer",
    "SessionAuth",
    "django_auth",
]

django_auth = SessionAuth()
