from ninja.security.apikey import APIKeyQuery, APIKeyCookie, APIKeyHeader
from ninja.security.http import HttpBearer, HttpBasicAuth
from ninja.security.session import SessionAuth


django_auth = SessionAuth()
