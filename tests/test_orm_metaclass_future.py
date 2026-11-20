from __future__ import annotations

from django.db import models

from ninja import ModelSchema, Schema


def test_custom_field_with_local_schema():
    class FutureModel(models.Model):
        name = models.CharField()

        class Meta:
            app_label = "tests"

    class TagSchema(Schema):
        label: str

    # postponed annotations: "TagSchema" is a string that only this
    # function's namespace resolves, so the class must build incomplete
    class FutureSchema(ModelSchema):
        tag: TagSchema

        class Meta:
            model = FutureModel
            fields = ["id", "name"]

    FutureSchema.model_rebuild()

    assert list(FutureSchema.model_fields) == ["id", "name", "tag"]
    instance = FutureSchema(id=1, name="n", tag={"label": "a"})
    assert instance.model_dump() == {"id": 1, "name": "n", "tag": {"label": "a"}}
