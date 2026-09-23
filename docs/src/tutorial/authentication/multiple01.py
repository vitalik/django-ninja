from django.utils.crypto import constant_time_compare

from ninja.security import APIKeyHeader, APIKeyQuery


class AuthCheck:
    def authenticate(self, request, key):
        if constant_time_compare(key, "supersecret"):
            return key


class QueryKey(AuthCheck, APIKeyQuery):
    pass


class HeaderKey(AuthCheck, APIKeyHeader):
    pass


@api.get("/multiple", auth=[QueryKey(), HeaderKey()])
def multiple(request):
    return f"Token = {request.auth}"
