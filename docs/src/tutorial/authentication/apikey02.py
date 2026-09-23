from django.utils.crypto import constant_time_compare

from ninja.security import APIKeyHeader


class ApiKey(APIKeyHeader):
    param_name = "X-API-Key"

    def authenticate(self, request, key):
        if constant_time_compare(key, "supersecret"):
            return key


header_key = ApiKey()


@api.get("/headerkey", auth=header_key)
def apikey(request):
    return f"Token = {request.auth}"
