from typing import List

from django.http import HttpRequest, QueryDict

from ninja import NinjaAPI
from ninja.parser import Parser
from ninja.testing import TestClient


class MyParser(Parser):
    "Default json parser"

    def parse_body(self, request: HttpRequest):
        "just splitting body to lines"
        return request.body.encode().splitlines()

    def parse_querydict(
        self, data: QueryDict, list_fields: List[str], request: HttpRequest
    ):
        "Turning empty Query params to None instead of empty string"
        result = super().parse_querydict(data, list_fields, request)
        for k, v in list(result.items()):
            if v == "":
                del result[k]
        return result


api = NinjaAPI(parser=MyParser())


@api.post("/test")
def operation(request, body: List[str], emptyparam: str = None):
    return {"emptyparam": emptyparam, "body": body}


def test_parser():
    client = TestClient(api)
    response = client.post("/test?emptyparam", body="test\nbar")
    assert response.status_code == 200, response.content
    assert response.json() == {"emptyparam": None, "body": ["test", "bar"]}
