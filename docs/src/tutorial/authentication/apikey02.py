from ninja import NinjaAPI
from ninja.security import APIKeyHeader

api = NinjaAPI()


class ApiKey(APIKeyHeader):
    param_name = "X-API-Key"

    def authenticate(self, request, key):
        if key == "supersecret":
            return key


header_key = ApiKey()


@api.get("/headerkey", auth=header_key)
def apikey(request):
    return f"Token = {request.auth}"
