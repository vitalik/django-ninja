from unittest.mock import patch

from ninja import NinjaAPI
from ninja.testing import TestClient


def test_examples():

    api = NinjaAPI()

    with patch("builtins.api", api, create=True):
        import docs.src.tutorial.form.code01  # noqa: F401
        import docs.src.tutorial.form.code02  # noqa: F401

        client = TestClient(api)

        assert client.post(
            "/items", data={"name": "Katana", "price": 299.00, "quantity": 10}
        ).json() == {
            "name": "Katana",
            "description": None,
            "price": 299.0,
            "quantity": 10,
        }

        assert client.post(
            "/items/1?q=test", data={"name": "Katana", "price": 299.00, "quantity": 10}
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

    with patch("builtins.api", api, create=True):
        import docs.src.tutorial.form.code03  # noqa: F401

        client = TestClient(api)

        assert client.post(
            "/items-blank-default",
            data={"name": "Katana", "price": "", "quantity": "", "in_stock": ""},
        ).json() == {
            "name": "Katana",
            "description": None,
            "in_stock": True,
            "price": 0.0,
            "quantity": 0,
        }
