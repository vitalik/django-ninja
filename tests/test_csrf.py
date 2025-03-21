import re

from django.conf import settings
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt, ensure_csrf_cookie

from ninja import NinjaAPI
from ninja.security import APIKeyCookie, APIKeyHeader, django_auth
from ninja.testing import TestClient as BaseTestClient


class TestClient(BaseTestClient):
    def _build_request(self, *args, **kwargs):
        request = super()._build_request(*args, **kwargs)
        request._dont_enforce_csrf_checks = False
        return request


csrf_OFF = NinjaAPI(urls_namespace="csrf_OFF")
csrf_ON = NinjaAPI(urls_namespace="csrf_ON", csrf=True)
csrf_ON_with_django_auth = NinjaAPI(
    urls_namespace="csrf_ON", csrf=True, auth=django_auth
)


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
    client = TestClient(csrf_OFF)
    assert client.post("/post", COOKIES=COOKIES).status_code == 200


def test_csrf_on():
    client = TestClient(csrf_ON)

    assert client.post("/post", COOKIES=COOKIES).status_code == 403

    # check with token in formdata
    response = client.post("/post", {"csrfmiddlewaretoken": TOKEN}, COOKIES=COOKIES)
    assert response.status_code == 200

    # check with headers
    response = client.post("/post", COOKIES=COOKIES, headers={"X-CSRFTOKEN": TOKEN})
    assert response.status_code == 200

    # exempt check
    assert client.post("/post/csrf_exempt", COOKIES=COOKIES).status_code == 200


def test_csrf_cookie_auth():
    "Cookie based authtentication should have csrf check by default"

    class CookieAuth(APIKeyCookie):
        def authenticate(self, request, key):
            return key == "test"

    cookie_auth = CookieAuth()
    api = NinjaAPI(auth=cookie_auth)

    @api.post("/test")
    def test_view(request):
        return {"success": True}

    client = TestClient(api)

    # No auth - access denied
    assert client.post("/test").status_code == 403

    # Cookie auth + valid csrf
    cookies = {"key": "test"}
    cookies.update(COOKIES)
    response = client.post("/test", COOKIES=cookies, headers={"X-CSRFTOKEN": TOKEN})
    assert response.status_code == 200, response.content

    # Cookie auth + INVALID csrf
    response = client.post(
        "/test", COOKIES=cookies, headers={"X-CSRFTOKEN": TOKEN + "invalid"}
    )
    assert response.status_code == 403, response.content

    # Turning off csrf on cookie, valid key, no csrf passed
    cookie_auth.csrf = False
    response = client.post("/test", COOKIES={"key": "test"})
    assert response.status_code == 200, response.content


def test_csrf_cookies_can_be_obtained():
    @csrf_ON.get("/obtain_csrf_token_get")
    @ensure_csrf_cookie
    def obtain_csrf_token_get(request):
        return JsonResponse(data={"success": True})

    @csrf_ON.post("/obtain_csrf_token_post")
    @ensure_csrf_cookie
    @csrf_exempt
    def obtain_csrf_token_post(request):
        return JsonResponse(data={"success": True})

    @csrf_ON_with_django_auth.get("/obtain_csrf_token_get", auth=None)
    @ensure_csrf_cookie
    def obtain_csrf_token_get_no_auth_route(request):
        return JsonResponse(data={"success": True})

    @csrf_ON_with_django_auth.post("/obtain_csrf_token_post", auth=None)
    @ensure_csrf_cookie
    @csrf_exempt
    def obtain_csrf_token_post_no_auth_route(request):
        return JsonResponse(data={"success": True})

    client = TestClient(csrf_ON)
    # can get csrf cookie through get
    response = client.get("/obtain_csrf_token_get")
    assert response.status_code == 200
    assert len(response.cookies["csrftoken"].value) > 0
    # can get csrf cookie through exempted post
    response = client.post("/obtain_csrf_token_post")
    assert response.status_code == 200
    assert len(response.cookies["csrftoken"].value) > 0
    # Now testing a route with disabled auth from a client with django_auth set globally also works
    client = TestClient(csrf_ON_with_django_auth)
    # can get csrf cookie through get on route with disabled auth
    response = client.get("/obtain_csrf_token_get")
    assert response.status_code == 200
    assert len(response.cookies["csrftoken"].value) > 0
    # can get csrf cookie through exempted post on route with disabled auth
    response = client.post("/obtain_csrf_token_post")
    assert response.status_code == 200
    assert len(response.cookies["csrftoken"].value) > 0


def test_docs():
    "Testing that docs are initializing csrf headers correctly"

    api = NinjaAPI(csrf=True)

    client = TestClient(api)
    resp = client.get("/docs")
    assert resp.status_code == 200
    csrf_token = re.findall(r'data-csrf-token="(.*?)"', resp.content.decode("utf8"))[0]
    assert len(csrf_token) > 0

    api.csrf = False
    resp = client.get("/docs")
    assert resp.status_code == 200
    csrf_token = re.findall(r'data-csrf-token="(.*?)"', resp.content.decode("utf8"))[0]
    assert len(csrf_token) == 0


def test_docs_cookie_auth():
    class CookieAuth(APIKeyCookie):
        def authenticate(self, request, key):
            return key == "test"

    class HeaderAuth(APIKeyHeader):
        def authenticate(self, request, key):
            return key == "test"

    api = NinjaAPI(csrf=False, auth=CookieAuth())
    client = TestClient(api)
    resp = client.get("/docs")
    csrf_token = re.findall(r'data-csrf-token="(.*?)"', resp.content.decode("utf8"))[0]
    assert len(csrf_token) > 0

    api = NinjaAPI(csrf=False, auth=HeaderAuth())
    client = TestClient(api)
    resp = client.get("/docs")
    csrf_token = re.findall(r'data-csrf-token="(.*?)"', resp.content.decode("utf8"))[0]
    assert len(csrf_token) == 0
