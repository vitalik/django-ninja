from ninja.security.apikey import APIKeyCookie, APIKeyHeader, APIKeyQuery
from ninja.security.http import HttpBasicAuth, HttpBearer
from ninja.security.session import SessionAuth, SessionAuthSuperUser,SessionAuthHasPerms,SessionAuthHasPerm

__all__ = [
    "APIKeyCookie",
    "APIKeyHeader",
    "APIKeyQuery",
    "HttpBasicAuth",
    "HttpBearer",
    "SessionAuth",
    "SessionAuthSuperUser",
    "django_auth",
    "django_auth_superuser",
    "SessionAuthHasPerm",
    "SessionAuthHasPerms",
]

django_auth = SessionAuth()
django_auth_superuser = SessionAuthSuperUser()
