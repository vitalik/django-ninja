from django.http import HttpResponse

from ninja import NinjaAPI
from ninja.testing import TestClient

api = NinjaAPI()


@api.get("/test-no-cookies")
def op_no_cookies(request):
    return {}


@api.get("/test-set-cookie")
def op_set_cookie(request):
    response = HttpResponse()
    response.set_cookie(key="sessionid", value="sessionvalue")
    return response


client = TestClient(api)


def test_cookies():
    assert bool(client.get("/test-no-cookies").cookies) is False
    assert "sessionid" in client.get("/test-set-cookie").cookies
