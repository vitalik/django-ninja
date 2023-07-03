from ninja import Schema


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


def test_schema_with_context():
    obj = ResolveWithKWargs.model_validate({"value": 10}, context={"extra": 10})
    assert obj.value == 20

    obj = ResolveWithContext.model_validate({"value": 2}, context={"extra": 2})
    assert obj.value == 4
