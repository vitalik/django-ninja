from ninja.security.apikey import APIKeyQuery, APIKeyCookie, APIKeyHeader
from ninja.security.http import HttpBearer, HttpBasicAuth


def django_auth(request):
    if request.user.is_authenticated:
        return request.user
