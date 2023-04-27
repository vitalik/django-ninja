import pytest

from ninja.renderers import JSONRenderer, PlainTextRenderer
from ninja import NinjaAPI
from ninja.testing import TestClient


@pytest.mark.parametrize(
    "renderer,expected_content_type",
    [
        (JSONRenderer, "application/json; charset=utf-8"),
        (PlainTextRenderer, "text/plain; charset=utf-8"),
    ],
)
def test_renderer_media_type(renderer, expected_content_type):
    api = NinjaAPI(renderer=renderer())

    @api.get("/1")
    def same_name(request):
        return None

    client = TestClient(api)
    response = client.get("/1")
    assert response.headers == {"Content-Type": expected_content_type}


@pytest.mark.parametrize(
    "renderer,expected_response",
    [
        (JSONRenderer, b"""{"key": "value"}"""),
        (PlainTextRenderer, b"""{'key': 'value'}"""),
    ],
)
def test_renderer_text(renderer, expected_response):
    api = NinjaAPI(renderer=renderer())

    @api.get("/1")
    def same_name(request):
        return {"key": "value"}

    client = TestClient(api)
    response = client.get("/1")
    assert response.content == expected_response
