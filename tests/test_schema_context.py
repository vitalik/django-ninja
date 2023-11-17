from ninja import NinjaAPI, Schema
from ninja.testing import TestClient


class ResolveWithKWargs(Schema):
    value: int

    @staticmethod
    def resolve_value(obj, **kwargs):
        context = kwargs["context"]
        return obj["value"] + context["extra"]


class ResolveWithContext(Schema):
    value: int

    @staticmethod
    def resolve_value(obj, context):
        return obj["value"] + context["extra"]


class DataWithRequestContext(Schema):
    value: dict = None
    other: dict = None

    @staticmethod
    def resolve_value(obj, context):
        result = {k: str(v) for k, v in context.items()}
        assert "request" in result, "request not in context"
        result["request"] = "<request>"  # making it static for easier testing
        return result


api = NinjaAPI()


@api.post("/resolve_ctx", response=DataWithRequestContext)
def resolve_ctx(request, data: DataWithRequestContext):
    return {"other": data.dict()}


client = TestClient(api)


def test_schema_with_context():
    obj = ResolveWithKWargs.model_validate({"value": 10}, context={"extra": 10})
    assert obj.value == 20

    obj = ResolveWithContext.model_validate({"value": 2}, context={"extra": 2})
    assert obj.value == 4

    obj = ResolveWithContext.from_orm({"value": 2}, context={"extra": 2})
    assert obj.value == 4


def test_request_context():
    resp = client.post("/resolve_ctx", json={})
    assert resp.status_code == 200, resp.content
    assert resp.json() == {
        "other": {"value": {"request": "<request>"}, "other": None},
        "value": {"request": "<request>", "response_status": "200"},
    }
