from django.utils.crypto import constant_time_compare

from ninja import Form, NinjaAPI
from ninja.security import HttpBearer


class GlobalAuth(HttpBearer):
    def authenticate(self, request, token):
        if constant_time_compare(token, "supersecret"):
            return token


api = NinjaAPI(auth=GlobalAuth())

# @api.get(...)
# def ...
# @api.post(...)
# def ...


@api.post("/token", auth=None)  # < overriding global auth
def get_token(request, username: str = Form(...), password: str = Form(...)):
    if username == "admin" and constant_time_compare(password, "giraffethinnknslong"):
        return {"token": "supersecret"}
