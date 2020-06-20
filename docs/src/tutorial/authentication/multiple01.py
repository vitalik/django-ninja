from ninja.security import APIKeyQuery, APIKeyHeader


class AuthCheck:
    def authenticate(self, request, key):
        if key == "supersecret":
            return key


class QueryKey(AuthCheck, APIKeyQuery):
    pass


class HeaderKey(AuthCheck, APIKeyHeader):
    pass


@api.get("/multiple", auth=[QueryKey(), HeaderKey()])
def multiple(request):
    return f"Token = {request.auth}"
