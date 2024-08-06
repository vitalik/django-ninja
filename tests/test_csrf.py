import re

from django.conf import settings
from django.views.decorators.csrf import csrf_exempt

from ninja import NinjaAPI, Router
from ninja.security import APIKeyCookie, APIKeyHeader
from ninja.testing import TestClient as BaseTestClient


class TestClient(BaseTestClient):
    def _build_request(self, *args, **kwargs):
        request = super()._build_request(*args, **kwargs)
        request._dont_enforce_csrf_checks = False
        return request


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


def test_docs_add_csrf():
    "Testing that docs are initializing csrf headers correctly"

    class CookieAuth(APIKeyCookie):
        def authenticate(self, request, key):
            return key == "test"

    api = NinjaAPI(csrf=False, auth=CookieAuth())  # `csrf=False` should be ignored

    @api.get("/test")
    def test_view(request):
        return {"success": True}

    client = TestClient(api)

    resp = client.get("/docs")
    assert resp.status_code == 200
    csrf_token = re.findall(r'data-csrf-token="(.*?)"', resp.content.decode("utf8"))[0]
    assert len(csrf_token) > 0

    assert hasattr(api, "_add_csrf")  # `api._add_csrf` should be set as cache

    resp = client.get("/docs")
    assert resp.status_code == 200
    csrf_token = re.findall(r'data-csrf-token="(.*?)"', resp.content.decode("utf8"))[0]
    assert len(csrf_token) > 0


def test_docs_add_csrf_by_operation():
    "Testing that docs are initializing csrf headers correctly"

    class CookieAuth(APIKeyCookie):
        def authenticate(self, request, key):
            return key == "test"

    api = NinjaAPI(csrf=False)  # `csrf=False` should be ignored

    @api.get("/test1", auth=CookieAuth())
    def test_view1(request):
        return {"success": True}

    @api.get("/test2")
    def test_view2(request):
        return {"success": True}

    client = TestClient(api)
    resp = client.get("/docs")
    assert resp.status_code == 200
    csrf_token = re.findall(r'data-csrf-token="(.*?)"', resp.content.decode("utf8"))[0]
    assert len(csrf_token) > 0


def test_docs_add_csrf_by_sub_router():
    "Testing that docs are initializing csrf headers correctly"

    class CookieAuth(APIKeyCookie):
        def authenticate(self, request, key):
            return key == "test"

    api = NinjaAPI(csrf=False)  # `csrf=False` should be ignored

    @api.get("/test1", auth=CookieAuth())
    def test_view1(request):
        return {"success": True}

    router = Router()

    @router.get("/test2")
    def test_view2(request):
        return {"success": True}

    api.add_router("/router", router)

    client = TestClient(api)
    resp = client.get("/docs")
    assert resp.status_code == 200
    csrf_token = re.findall(r'data-csrf-token="(.*?)"', resp.content.decode("utf8"))[0]
    assert len(csrf_token) > 0


def test_docs_do_not_add_csrf():
    class HeaderAuth(APIKeyHeader):
        def authenticate(self, request, key):
            return key == "test"

    api = NinjaAPI(csrf=True, auth=HeaderAuth())  # `csrf=True` should be ignored

    @api.get("/test")
    def test_view(request):
        return {"success": True}

    client = TestClient(api)
    resp = client.get("/docs")
    csrf_token = re.findall(r'data-csrf-token="(.*?)"', resp.content.decode("utf8"))[0]
    assert len(csrf_token) == 0
