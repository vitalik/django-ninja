from ninja import NinjaAPI, Form, Router
from ninja.security import HttpBearer


class RouterAuth(HttpBearer):
    def authenticate(self, request, token):
        if token == "pupersecret":
            return token


api = NinjaAPI()
router = Router(auth=RouterAuth())

# @router.get(...)
# def ...
# @router.post(...)
# def ...

api.add_router('', router)

@router.post("/token", auth=None)  # < overriding router auth as well as global one
def get_token(request, username: str = Form(...), password: str = Form(...)):
    if username == "admin" and password == "giraffethinnknslong":
        return {"token": "supersecret"}
