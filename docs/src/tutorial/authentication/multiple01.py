from ninja.security import APIKeyQuery, APIKeyHeader, HttpBearer


class AuthCheck:
    def authenticate(self, request, key):
        if key == "supersecret":
            return key


class QueryKey(AuthCheck, APIKeyQuery):
    pass


class HeaderKey(AuthCheck, APIKeyHeader):
    pass


class AuthBearer(HttpBearer):
    def authenticate(self, request, token):
        if token == "anothersupersecret":
            return token


@api.get("/multiple", auth=(QueryKey() | HeaderKey() | AuthBearer()))
def multiple(request):
    return f"Token = {request.auth}"
