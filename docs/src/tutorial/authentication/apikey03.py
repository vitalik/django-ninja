from ninja import NinjaAPI
from ninja.security import APIKeyCookie

api = NinjaAPI()


class CookieKey(APIKeyCookie):
    def authenticate(self, request, key):
        if key == "supersecret":
            return key


cookie_key = CookieKey()


@api.get("/cookiekey", auth=cookie_key)
def apikey(request):
    return f"Token = {request.auth}"
