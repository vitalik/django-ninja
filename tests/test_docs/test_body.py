from unittest.mock import patch

from ninja import NinjaAPI
from ninja.testing import TestClient


def test_examples():
    api = NinjaAPI()

    with patch("builtins.api", api, create=True):
        import docs.src.tutorial.body.code01  # noqa: F401
        import docs.src.tutorial.body.code02  # noqa: F401
        import docs.src.tutorial.body.code03  # noqa: F401

        client = TestClient(api)

        assert client.post(
            "/items", json={"name": "Katana", "price": 299.00, "quantity": 10}
        ).json() == {
            "name": "Katana",
            "description": None,
            "price": 299.0,
            "quantity": 10,
        }

        assert client.put(
            "/items/1", json={"name": "Katana", "price": 299.00, "quantity": 10}
        ).json() == {
            "item_id": 1,
            "item": {
                "name": "Katana",
                "description": None,
                "price": 299.0,
                "quantity": 10,
            },
        }

        assert client.post(
            "/items/1?q=test", json={"name": "Katana", "price": 299.00, "quantity": 10}
        ).json() == {
            "item_id": 1,
            "q": "test",
            "item": {
                "name": "Katana",
                "description": None,
                "price": 299.0,
                "quantity": 10,
            },
        }
