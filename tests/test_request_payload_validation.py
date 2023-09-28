from pydantic import Extra

from ninja import NinjaAPI, Query, Schema
from ninja.testing import TestClient

api = NinjaAPI()


class TestSchema(Schema, extra=Extra.forbid):
    a: str


@api.get("/")
def get_endpoint(request, params: TestSchema = Query(...)):
    # succeeds when passing extra params
    return params


@api.post("/")
def post_endpoint(request, body: TestSchema):
    # fails when passing extra params
    return body


def test_extra_forbid_validation():
    client = TestClient(api)
    get_response = client.get("/?a=value&b=value2")
    assert get_response.status_code == 422
    assert get_response.json()["detail"][0]["msg"] == "extra fields not permitted"
    post_response = client.post("/", json={"a": "value", "b": "value2"})
    assert post_response.status_code == 422
    assert post_response.json()["detail"][0]["msg"] == "extra fields not permitted"
