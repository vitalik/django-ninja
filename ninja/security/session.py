from django.conf import settings
from ninja.security.apikey import APIKeyCookie


class SessionAuth(APIKeyCookie):
    "Reusing Django session authentication"
    param_name = settings.SESSION_COOKIE_NAME

    def authenticate(self, request, key):
        if request.user.is_authenticated:
            return request.user
