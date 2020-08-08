from unittest.mock import patch
from ninja import NinjaAPI
from client import NinjaClient


def test_examples():

    api = NinjaAPI()

    with patch("builtins.api", api, create=True):
        import docs.src.tutorial.query.code01
        import docs.src.tutorial.query.code02
        import docs.src.tutorial.query.code03
        import docs.src.tutorial.query.code010

        client = NinjaClient(api)

        # Defaults
        assert client.get("/weapons").json() == [
            "Ninjato",
            "Shuriken",
            "Katana",
            "Kama",
            "Kunai",
            "Naginata",
            "Yari",
        ]

        assert client.get("/weapons?offset=0&limit=3").json() == [
            "Ninjato",
            "Shuriken",
            "Katana",
        ]

        assert client.get("/weapons?offset=2&limit=2").json() == [
            "Katana",
            "Kama",
        ]

        # Required/Optional

        assert client.get("/weapons/search?offset=1&q=k").json() == [
            "Katana",
            "Kama",
            "Kunai",
        ]

        # Coversion

        # fmt: off
        assert client.get("/example?b=1").json() == [None, True, None, None]
        assert client.get("/example?b=True").json() == [None, True, None, None]
        assert client.get("/example?b=true").json() == [None, True, None, None]
        assert client.get("/example?b=on").json() == [None, True, None, None]
        assert client.get("/example?b=yes").json() == [None, True, None, None]
        assert client.get("/example?b=0").json() == [None, False, None, None]
        assert client.get("/example?b=no").json() == [None, False, None, None]
        assert client.get("/example?b=false").json() == [None, False, None, None]
        assert client.get("/example?d=1577836800").json() == [None, None, "2020-01-01", None]
        assert client.get("/example?d=2020-01-01").json() == [None, None, "2020-01-01", None]
        # fmt: on

        # Schema

        assert client.get("/filter").json() == {
            "filters": {"limit": 100, "offset": None, "query": None}
        }
        assert client.get("/filter?limit=10").json() == {
            "filters": {"limit": 10, "offset": None, "query": None}
        }
        assert client.get("/filter?offset=10").json() == {
            "filters": {"limit": 100, "offset": 10, "query": None}
        }
        assert client.get("/filter?query=10").json() == {
            "filters": {"limit": 100, "offset": None, "query": "10"}
        }

        schema = api.get_openapi_schema("")
        params = schema["paths"]["/filter"]["get"]["parameters"]
        assert params == [
            {
                "in": "query",
                "name": "limit",
                "required": False,
                "schema": {"title": "Limit", "default": 100, "type": "integer"},
            },
            {
                "in": "query",
                "name": "offset",
                "required": False,
                "schema": {"title": "Offset", "type": "integer"},
            },
            {
                "in": "query",
                "name": "query",
                "required": False,
                "schema": {"title": "Query", "type": "string"},
            },
        ]
