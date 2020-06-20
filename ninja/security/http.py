from base64 import b64decode
from urllib.parse import unquote
from ninja.compatibility import get_headers
from ninja.security.base import AuthBase


class HttpAuthBase(AuthBase):
    openapi_type = "http"


class HttpBearer(HttpAuthBase):
    openapi_scheme = "bearer"
    header = "Authorization"

    def __call__(self, request):
        headers = get_headers(request)
        auth_value = headers.get(self.header)
        if not auth_value:
            return
        parts = auth_value.split(" ")

        if parts[0].lower() != "bearer":
            print(f"Unexpected auth - '{auth_value}'")
            return
        token = " ".join(parts[1:])
        return self.authenticate(request, token)

    def authenticate(self, request, token):
        raise NotImplementedError("Please implement authenticate(self, request, token)")


class DecodeError(Exception):
    pass


class HttpBasicAuth(HttpAuthBase):  # TODO: maybe HttpBasicAuthBase
    openapi_scheme = "basic"
    header = "Authorization"

    def __call__(self, request):
        headers = get_headers(request)
        auth_value = headers.get(self.header)
        if not auth_value:
            return

        try:
            username, password = self.decode_authorization(auth_value)
        except DecodeError as e:
            print(e)
            return
        return self.authenticate(request, username, password)

    def authenticate(self, request, username, password):
        raise NotImplementedError(
            "Please implement authenticate(self, request, username, password)"
        )

    def decode_authorization(self, value):
        parts = value.split(" ")
        if len(parts) == 1:
            user_pass_encoded = parts[0]
        elif len(parts) == 2 and parts[0].lower() == "basic":
            user_pass_encoded = parts[1]
        else:
            raise DecodeError("Invlid Authorization header")

        try:
            username, password = b64decode(user_pass_encoded).decode().split(":", 1)
            return unquote(username), unquote(password)
        except Exception as e:
            print(e)
            raise DecodeError("Invlid Authorization header") from e
