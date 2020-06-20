import pytest
from unittest.mock import Mock, patch
from ninja import NinjaAPI
from client import NinjaClient


def test_intro():
    from docs.src.tutorial.authentication.code001 import api

    client = NinjaClient(api)
    assert client.get("/pets").status_code == 401

    user = Mock()
    user.is_authenticated = True

    response = client.get("/pets", user=user)
    assert response.status_code == 200


@pytest.mark.django_db
def test_examples():
    from someapp.models import Client

    api = NinjaAPI()
    Client.objects.create(key="12345")

    with patch("builtins.api", api, create=True):
        import docs.src.tutorial.authentication.code002
        import docs.src.tutorial.authentication.apikey01
        import docs.src.tutorial.authentication.apikey02
        import docs.src.tutorial.authentication.apikey03
        import docs.src.tutorial.authentication.basic01
        import docs.src.tutorial.authentication.bearer01
        import docs.src.tutorial.authentication.code001
        import docs.src.tutorial.authentication.schema01
        import docs.src.tutorial.authentication.multiple01

        client = NinjaClient(api)

        response = client.get("/ipwhiltelist", META={"REMOTE_ADDR": "127.0.0.1"})
        assert response.status_code == 401
        response = client.get("/ipwhiltelist", META={"REMOTE_ADDR": "8.8.8.8"})
        assert response.status_code == 200

        # Api key --------------------------------

        response = client.get("/apikey")
        assert response.status_code == 401
        response = client.get("/apikey?api_key=12345")
        assert response.status_code == 200

        response = client.get("/headerkey")
        assert response.status_code == 401
        response = client.get("/headerkey", headers={"X-API-Key": "supersecret"})
        assert response.status_code == 200

        response = client.get("/cookiekey")
        assert response.status_code == 401
        response = client.get("/cookiekey", COOKIES={"key": "supersecret"})
        assert response.status_code == 200

        # Basic http --------------------------------

        response = client.get("/basic")
        assert response.status_code == 401
        response = client.get(
            "/basic", headers={"Authorization": "Basic YWRtaW46c2VjcmV0"}
        )
        assert response.status_code == 200
        assert response.json() == {"httpuser": "admin"}

        # Bearer http --------------------------------

        response = client.get("/bearer")
        assert response.status_code == 401

        response = client.get(
            "/bearer", headers={"Authorization": "Bearer supersecret"}
        )
        assert response.status_code == 200

        # Multiple ------------------------------------
        assert client.get("/multiple").status_code == 401
        assert client.get("/multiple?key=supersecret").status_code == 200
        assert (
            client.get("/multiple", headers={"key": "supersecret"}).status_code == 200
        )


def test_global():
    from docs.src.tutorial.authentication.global01 import api

    @api.get("/somemethod")
    def mustbeauthed(request):
        return {"auth": request.auth}

    client = NinjaClient(api)

    assert client.get("/somemethod").status_code == 401

    resp = client.post(
        "/token", POST={"username": "admin", "password": "giraffethinnknslong"}
    )
    assert resp.status_code == 200
    assert resp.json() == {"token": "supersecret"}

    resp = client.get("/somemethod", headers={"Authorization": "Bearer supersecret"})
    assert resp.status_code == 200
