import pytest
from django.db import models

from ninja import ModelSchema
from ninja.errors import ConfigError


def test_simple():
    class User(models.Model):
        firstname = models.CharField()
        lastname = models.CharField(blank=True, null=True)

        class Meta:
            app_label = "tests"

    class SampleSchema(ModelSchema):
        class Config:
            model = User
            model_fields = ["firstname", "lastname"]

        def hello(self):
            return f"Hello({self.firstname})"

    assert SampleSchema.json_schema() == {
        "title": "SampleSchema",
        "type": "object",
        "properties": {
            "firstname": {"title": "Firstname", "type": "string"},
            "lastname": {
                "anyOf": [{"type": "string"}, {"type": "null"}],
                "title": "Lastname",
            },
        },
        "required": ["firstname"],
    }

    assert SampleSchema(firstname="ninja", lastname="Django").hello() == "Hello(ninja)"

    # checking exclude ----------------------------------------------
    class SampleSchema2(ModelSchema):
        class Meta:
            model = User
            exclude = ["lastname"]

    assert SampleSchema2.json_schema() == {
        "title": "SampleSchema2",
        "type": "object",
        "properties": {
            "id": {"anyOf": [{"type": "integer"}, {"type": "null"}], "title": "ID"},
            "firstname": {"title": "Firstname", "type": "string"},
        },
        "required": ["firstname"],
    }


def test_custom():
    class CustomModel(models.Model):
        f1 = models.CharField()
        f2 = models.CharField(blank=True, null=True)

        class Meta:
            app_label = "tests"

    class CustomSchema(ModelSchema):
        f3: int
        f4: int = 1
        _private: str = "<secret>"  # private should be ignored

        class Meta:
            model = CustomModel
            fields = ["f1", "f2"]

    assert CustomSchema.json_schema() == {
        "title": "CustomSchema",
        "type": "object",
        "properties": {
            "f1": {"title": "F1", "type": "string"},
            "f2": {"anyOf": [{"type": "string"}, {"type": "null"}], "title": "F2"},
            "f3": {"title": "F3", "type": "integer"},
            "f4": {"title": "F4", "default": 1, "type": "integer"},
        },
        "required": ["f3", "f1"],
    }


def test_config():
    class Category(models.Model):
        title = models.CharField()

        class Meta:
            app_label = "tests"

    with pytest.raises(ConfigError):

        class CategorySchema(ModelSchema):
            class Meta:
                model = Category


def test_optional():
    class OptModel(models.Model):
        title = models.CharField()
        other = models.CharField(null=True)
        extra = models.IntegerField()
        count = models.IntegerField(default=0, null=True)

        class Meta:
            app_label = "tests"

    class OptSchema(ModelSchema):
        class Meta:
            model = OptModel
            fields = "__all__"
            fields_optional = ["title"]

    class OptSchema2(ModelSchema):
        class Meta:
            model = OptModel
            fields = "__all__"
            fields_optional = "__all__"

    assert OptSchema.json_schema().get("required") == ["extra"]
    assert OptSchema.json_schema()["properties"] == {
        "id": {"anyOf": [{"type": "integer"}, {"type": "null"}], "title": "ID"},
        "title": {"anyOf": [{"type": "string"}, {"type": "null"}], "title": "Title"},
        "other": {"anyOf": [{"type": "string"}, {"type": "null"}], "title": "Other"},
        "extra": {"title": "Extra", "type": "integer"},
        "count": {
            "anyOf": [{"type": "integer"}, {"type": "null"}],
            "default": 0,
            "title": "Count",
        },
    }

    assert OptSchema2.json_schema().get("required") is None
    assert OptSchema2.json_schema()["properties"] == {
        "id": {"anyOf": [{"type": "integer"}, {"type": "null"}], "title": "ID"},
        "title": {"anyOf": [{"type": "string"}, {"type": "null"}], "title": "Title"},
        "other": {"anyOf": [{"type": "string"}, {"type": "null"}], "title": "Other"},
        "extra": {"anyOf": [{"type": "integer"}, {"type": "null"}], "title": "Extra"},
        "count": {
            "anyOf": [{"type": "integer"}, {"type": "null"}],
            "default": 0,
            "title": "Count",
        },
    }


def test_fields_all():
    class SomeModel(models.Model):
        field1 = models.CharField()
        field2 = models.CharField(blank=True, null=True)

        class Meta:
            app_label = "tests"

    class SomeSchema(ModelSchema):
        class Meta:
            model = SomeModel
            fields = "__all__"

    print(SomeSchema.json_schema())
    assert SomeSchema.json_schema() == {
        "title": "SomeSchema",
        "type": "object",
        "properties": {
            "id": {"anyOf": [{"type": "integer"}, {"type": "null"}], "title": "ID"},
            "field1": {"title": "Field1", "type": "string"},
            "field2": {
                "anyOf": [{"type": "string"}, {"type": "null"}],
                "title": "Field2",
            },
        },
        "required": ["field1"],
    }


def test_model_schema_without_config():
    with pytest.raises(
        ConfigError,
        match=r"ModelSchema class 'NoConfigSchema' requires a 'Meta' \(or a 'Config'\) subclass",
    ):

        class NoConfigSchema(ModelSchema):
            x: int
