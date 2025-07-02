from unittest.mock import MagicMock

import pytest

from ninja import NinjaAPI, Router
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
mock_middleware3 = MagicMock()
mock_middleware3.side_effect = dummy_middleware


@pytest.fixture(autouse=True, scope="function")
def reset_middlewares():
    mock_middleware1.reset_mock()
    mock_middleware2.reset_mock()
    mock_middleware3.reset_mock()


api = NinjaAPI(middlewares=[mock_middleware2, mock_middleware1])
router = Router(middlewares=[mock_middleware3])


@api.get("/global")
def global_op(request):
    return "global response"


@router.get("/router")
def router_op(request):
    return "router response"


api.add_router("/", router)


client = TestClient(api)


def test_api_middlewares():
    """
    Test that the API middlewares are called in the correct order.
    """
    response = client.get("/global")
    assert response.status_code == 200
    assert mock_middleware2.call_count == 1
    assert mock_middleware1.call_count == 1
    # Assert that mock_middleware2 was called with mock_middleware1 as the next method
    assert mock_middleware2.call_args[1].get("next_method").func == mock_middleware1
    assert mock_middleware1.call_args[1].get("next_method") == global_op


def test_api_middlewares_with_router_middlewares():
    """
    Test that the API middlewares are called in the correct order.
    """
    response = client.get("/router")
    assert response.status_code == 200
    assert mock_middleware3.call_count == 1
    assert mock_middleware2.call_count == 1
    assert mock_middleware1.call_count == 1
    # Assert that mock_middleware2 was called with mock_middleware1 as the next method
    assert mock_middleware2.call_args[1].get("next_method").func == mock_middleware1
    assert mock_middleware1.call_args[1].get("next_method").func == mock_middleware3
    # Assert that mock_middleware3 was called with router_op as the next method
    assert mock_middleware3.call_args[1].get("next_method") == router_op
