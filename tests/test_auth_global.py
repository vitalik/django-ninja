from ninja import NinjaAPI
from ninja.security import APIKeyQuery
from client import NinjaClient


class KeyQuery1(APIKeyQuery):
    def authenticate(self, request, key):
        if key == "k1":
            return key


class KeyQuery2(APIKeyQuery):
    def authenticate(self, request, key):
        if key == "k2":
            return key


api = NinjaAPI(auth=KeyQuery1())


@api.get("/default")
def default(request):
    return {"auth": request.auth}


@api.api_operation(["POST", "PATCH"], "/multi-method-no-auth")
def multi_no_auth(request):
    return {"auth": request.auth}


@api.api_operation(["POST", "PATCH"], "/multi-method-auth", auth=KeyQuery2())
def multi_auth(request):
    return {"auth": request.auth}


client = NinjaClient(api)


def test_multi():
    assert client.get("/default").status_code == 401
    assert client.get("/default?key=k1").json() == {"auth": "k1"}

    assert client.post("/multi-method-no-auth").status_code == 401
    assert client.post("/multi-method-no-auth?key=k1").json() == {"auth": "k1"}

    assert client.patch("/multi-method-no-auth").status_code == 401
    assert client.patch("/multi-method-no-auth?key=k1").json() == {"auth": "k1"}

    assert client.post("/multi-method-auth?key=k1").status_code == 401
    assert client.patch("/multi-method-auth?key=k1").status_code == 401

    assert client.post("/multi-method-auth?key=k2").json() == {"auth": "k2"}
    assert client.patch("/multi-method-auth?key=k2").json() == {"auth": "k2"}
