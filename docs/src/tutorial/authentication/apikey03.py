from django.utils.crypto import constant_time_compare

from ninja.security import APIKeyCookie


class CookieKey(APIKeyCookie):
    def authenticate(self, request, key):
        if constant_time_compare(key, "supersecret"):
            return key


cookie_key = CookieKey()


@api.get("/cookiekey", auth=cookie_key)
def apikey(request):
    return f"Token = {request.auth}"
