from ninja.security import APIKeyCookie


class CookieKey(APIKeyCookie):
    def authenticate(self, request, key):
        if key == "supersecret":
            return key


cookie_key = CookieKey()


@api.get("/cookiekey", auth=cookie_key)
def apikey(request):
    return f"Token = {request.auth}"
