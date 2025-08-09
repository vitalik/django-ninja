from unittest.mock import MagicMock

import pytest

from ninja import Header, Router
from ninja.testing import TestClient


def dummy_middleware(*args, next_method, **kwargs):
    """
    A dummy middleware function that simulates processing.
    It calls the next method in the middleware chain.
    """
    return next_method(*args, **kwargs)


mock_middleware1 = MagicMock()
mock_middleware1.side_effect = dummy_middleware
mock_middleware2 = MagicMock()
mock_middleware2.side_effect = dummy_middleware

router = Router(middlewares=[mock_middleware1, mock_middleware2])


@pytest.fixture(autouse=True, scope="function")
def reset_middlewares():
    mock_middleware1.reset_mock()
    mock_middleware2.reset_mock()


@router.get("/test")
def mock_view(request, user_agent: str = Header(...)):
    return user_agent


client = TestClient(router)


@pytest.mark.parametrize(
    "path,expected_status,expected_response",
    [
        ("/test", 200, "Ninja"),
    ],
)
def test_request_middlewares(path, expected_status, expected_response):
    response = client.get(
        path,
        headers={"User-Agent": "Ninja", "Content-Length": "10"},
        COOKIES={"weapon": "shuriken"},
    )
    assert response.status_code == expected_status, response.content
    assert response.json() == expected_response
    assert mock_middleware1.call_count == 1
    assert mock_middleware2.call_count == 1
    # Assert that mock_middleware1 was called with mock_middleware2 as the next method
    assert mock_middleware1.call_args[1].get("next_method").func == mock_middleware2
    assert mock_middleware2.call_args[1].get("next_method") == mock_view
