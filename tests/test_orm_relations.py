from django.db import models
from django.test.utils import isolate_apps
from pydantic import AliasGenerator, ConfigDict
from pydantic.alias_generators import to_camel, to_pascal

from ninja import ModelSchema, NinjaAPI
from ninja.orm import create_schema
from ninja.testing import TestClient


def test_manytomany():
    class SomeRelated(models.Model):
        f = models.CharField()

        class Meta:
            app_label = "tests"

    class ModelWithM2M(models.Model):
        m2m = models.ManyToManyField(SomeRelated, blank=True)

        class Meta:
            app_label = "tests"

    WithM2MSchema = create_schema(ModelWithM2M, exclude=["id"])

    api = NinjaAPI()

    @api.post("/bar")
    def post_with_m2m(request, payload: WithM2MSchema):
        return payload.dict()

    client = TestClient(api)

    response = client.post("/bar", json={"m2m": [1, 2]})
    assert response.status_code == 200, str(response.json())
    assert response.json() == {"m2m": [1, 2]}

    response = client.post("/bar", json={"m2m": []})
    assert response.status_code == 200, str(response.json())
    assert response.json() == {"m2m": []}


@isolate_apps("tests")
def test_foreignkey_id_field_honors_alias_generator():
    """A ForeignKey's generated ``_id`` field must honor the schema's
    alias_generator like every other field, instead of staying snake_case while
    the rest of the schema is transformed (see #1691)."""

    class RelTarget(models.Model):
        class Meta:
            app_label = "tests"

    class RelSource(models.Model):
        target = models.ForeignKey(RelTarget, on_delete=models.CASCADE)
        some_value = models.CharField(max_length=10)

        class Meta:
            app_label = "tests"

    class SourceSchema(ModelSchema):
        model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)

        class Meta:
            model = RelSource
            fields = ["id", "target", "some_value"]

    aliases = {name: f.alias for name, f in SourceSchema.model_fields.items()}
    # The FK id field is camelCased just like the plain field, not left snake_case.
    assert aliases["target"] == "targetId"
    assert aliases["some_value"] == "someValue"


@isolate_apps("tests")
def test_foreignkey_id_field_honors_directional_alias_generator():
    """An ``AliasGenerator`` may set ``validation_alias`` and ``serialization_alias``
    independently (with no plain ``alias``). The FK ``_id`` field must pick up each
    direction just like an ordinary field, so validation and ``by_alias`` dumping
    both round-trip (see #1691)."""

    class RelTarget(models.Model):
        class Meta:
            app_label = "tests"

    class RelSource(models.Model):
        target = models.ForeignKey(RelTarget, on_delete=models.CASCADE)
        some_value = models.CharField(max_length=10)

        class Meta:
            app_label = "tests"

    class SourceSchema(ModelSchema):
        model_config = ConfigDict(
            alias_generator=AliasGenerator(
                validation_alias=to_camel, serialization_alias=to_pascal
            )
        )

        class Meta:
            model = RelSource
            fields = ["id", "target", "some_value"]

    target_field = SourceSchema.model_fields["target"]
    plain_field = SourceSchema.model_fields["some_value"]
    # The FK id field carries both directional aliases, just like a plain field.
    assert target_field.validation_alias == "targetId"
    assert target_field.serialization_alias == "TargetId"
    assert plain_field.validation_alias == "someValue"
    assert plain_field.serialization_alias == "SomeValue"

    # Runtime: validation consumes the camelCase validation alias...
    instance = SourceSchema.model_validate({"targetId": 5, "someValue": "ok"})
    assert instance.target == 5
    assert instance.some_value == "ok"

    # ...and serialization emits the PascalCase serialization alias.
    dumped = instance.model_dump(by_alias=True)
    assert dumped["TargetId"] == 5
    assert dumped["SomeValue"] == "ok"
