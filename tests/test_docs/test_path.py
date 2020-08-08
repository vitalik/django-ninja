from unittest.mock import patch
from ninja import NinjaAPI
from client import NinjaClient


def test_examples():

    api = NinjaAPI()

    with patch("builtins.api", api, create=True):
        import docs.src.tutorial.path.code010

        client = NinjaClient(api)

        response = client.get("/events/2020/1/1")
        assert response.json() == {"date": "2020-01-01"}
        schema = api.get_openapi_schema("")
        events_params = schema["paths"]["/events/{year}/{month}/{day}"]["get"][
            "parameters"
        ]
        # print(events_params, "!!")
        assert events_params == [
            {
                "in": "path",
                "name": "year",
                "required": True,
                "schema": {"title": "Year", "type": "integer"},
            },
            {
                "in": "path",
                "name": "month",
                "required": True,
                "schema": {"title": "Month", "type": "integer"},
            },
            {
                "in": "path",
                "name": "day",
                "required": True,
                "schema": {"title": "Day", "type": "integer"},
            },
        ]
