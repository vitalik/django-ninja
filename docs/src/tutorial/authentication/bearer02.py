from ninja import NinjaAPI
from ninja.security import HttpBearer

api = NinjaAPI()

class InvalidToken(Exception):
    pass

@api.exception_handler(InvalidToken)
def on_invalid_token(request, exc):
    return api.create_response(request, {"detail": "Invalid token supplied"}, status=401)

class AuthBearer(HttpBearer):
    def authenticate(self, request, token):
        if token == "supersecret":
            return token
        raise InvalidToken


@api.get("/bearer", auth=AuthBearer())
def bearer(request):
    return {"token": request.auth}
