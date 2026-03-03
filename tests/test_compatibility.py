"""Test Python 3.14 compatibility for ModelSchema annotations.

Python 3.14 no longer puts __annotations__ in the class namespace during
metaclass __new__ (PEP 749). This broke ModelSchemaMetaclass which reads
annotations from namespace to build custom_fields.
issues 1652, 1580
"""

from django.db import models
from ninja import ModelSchema, Schema


def test_modelschema_custom_annotation():
    """Custom type annotation on ModelSchema field should override the Django field type."""

    class CompatTestModel(models.Model):
        name = models.CharField(max_length=100)
        value = models.CharField(max_length=100)

        class Meta:
            app_label = "tests"

    class CompatTestModelSchema(ModelSchema):
        value: int  # override CharField -> int

        class Meta:
            model = CompatTestModel
            fields = ["name", "value"]

    assert CompatTestModelSchema.model_fields["value"].annotation is int


def test_modelschema_fk_schema_annotation():
    """FK field annotated with a nested Schema should use that schema, not the raw DB type."""

    class CompatParentModel(models.Model):
        title = models.CharField(max_length=100)

        class Meta:
            app_label = "tests"

    class CompatChildModel(models.Model):
        name = models.CharField(max_length=100)
        parent = models.ForeignKey(CompatParentModel, on_delete=models.CASCADE)

        class Meta:
            app_label = "tests"

    class CompatParentSchema(Schema):
        title: str

    class CompatChildSchema(ModelSchema):
        parent: CompatParentSchema

        class Meta:
            model = CompatChildModel
            fields = ["name", "parent"]

    assert CompatChildSchema.model_fields["parent"].annotation is CompatParentSchema
