"""A websocket route served through Django's WSGI handler explains what is missing."""

from django.test import Client, override_settings
from django.urls import path

from ninja import NinjaAPI, WebSocket

api = NinjaAPI(urls_namespace="ws-wsgi")


@api.websocket("/ws")
async def ws_handler(websocket: WebSocket):
    pass  # pragma: no cover


urlpatterns = [path("api/", api.urls)]


@override_settings(ROOT_URLCONF=__name__)
def test_upgrade_request_through_wsgi_returns_426():
    client = Client()

    response = client.get(
        "/api/ws", HTTP_UPGRADE="websocket", HTTP_CONNECTION="Upgrade"
    )
    assert response.status_code == 426
    detail = response.json()["detail"]
    assert "WSGI servers do not support WebSockets" in detail
    assert "ninja.asgi.get_asgi_application()" in detail

    response = client.get("/api/ws")
    assert response.status_code == 426
    assert response.json() == {
        "detail": "This endpoint only accepts WebSocket connections."
    }
