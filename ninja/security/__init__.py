from ninja.security.apikey import APIKeyCookie, APIKeyHeader, APIKeyQuery
from ninja.security.http import HttpBasicAuth, HttpBearer
from ninja.security.session import SessionAuth

django_auth = SessionAuth()
