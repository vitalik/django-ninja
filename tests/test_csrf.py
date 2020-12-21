from django.views.decorators import csrf
import pytest
from ninja import NinjaAPI
from ninja.security import APIKeyCookie
from ninja.errors import ConfigError
from django.conf import settings
from django.views.decorators.csrf import csrf_exempt
from client import NinjaClient


csrf_OFF = NinjaAPI(urls_namespace="csrf_OFF")
csrf_ON = NinjaAPI(urls_namespace="csrf_ON", csrf=True)


@csrf_OFF.post("/post")
def post_off(request):
    return {"success": True}


@csrf_ON.post("/post")
def post_on(request):
    return {"success": True}


@csrf_ON.post("/post/csrf_exempt")
@csrf_exempt
def post_on_with_exempt(request):
    return {"success": True}


TOKEN = "1bcdefghij2bcdefghij3bcdefghij4bcdefghij5bcdefghij6bcdefghijABCD"
COOKIES = {settings.CSRF_COOKIE_NAME: TOKEN}


def test_csrf_off():
    client = NinjaClient(csrf_OFF)
    assert client.post("/post", COOKIES=COOKIES).status_code == 200


def test_csrf_on():
    client = NinjaClient(csrf_ON)

    assert client.post("/post", COOKIES=COOKIES).status_code == 403

    # check with token in formdata
    response = client.post("/post", {"csrfmiddlewaretoken": TOKEN}, COOKIES=COOKIES)
    assert response.status_code == 200

    # check with headers
    response = client.post("/post", COOKIES=COOKIES, headers={"X-CSRFTOKEN": TOKEN})
    assert response.status_code == 200

    # exempt check
    assert client.post("/post/csrf_exempt", COOKIES=COOKIES).status_code == 200


def test_raises_on_cookie_auth():
    "It should raise if user picked Cookie based auth and csrf=False"

    class Auth(APIKeyCookie):
        def authenticate(self, request, key):
            return request.COOKIES[key] == "foo"

    api = NinjaAPI(auth=Auth(), csrf=False)

    @api.get("/some")
    def some_method(request):
        pass

    with pytest.raises(ConfigError):
        api._validate()
