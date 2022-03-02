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

    # print(SampleSchema.schema())
    assert SampleSchema.schema() == {
        "title": "SampleSchema",
        "type": "object",
        "properties": {
            "firstname": {"title": "Firstname", "type": "string"},
            "lastname": {"title": "Lastname", "type": "string"},
        },
        "required": ["firstname"],
    }

    assert SampleSchema(firstname="ninja").hello() == "Hello(ninja)"

    # checking exclude ----------------------------------------------
    class SampleSchema2(ModelSchema):
        class Config:
            model = User
            model_exclude = ["lastname"]

    assert SampleSchema2.schema() == {
        "title": "SampleSchema2",
        "type": "object",
        "properties": {
            "id": {"title": "Id", "type": "integer"},
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
        f5 = ""  # not annotated should be ignored
        _private: str = "<secret>"  # private should be ignored

        class Config:
            model = CustomModel
            model_fields = ["f1", "f2"]

    print(CustomSchema.schema())
    assert CustomSchema.schema() == {
        "title": "CustomSchema",
        "type": "object",
        "properties": {
            "f1": {"title": "F1", "type": "string"},
            "f2": {"title": "F2", "type": "string"},
            "f3": {"title": "F3", "type": "integer"},
            "f4": {"title": "F4", "default": 1, "type": "integer"},
        },
        "required": ["f1", "f3"],
    }


def test_config():
    class Category(models.Model):
        title = models.CharField()

        class Meta:
            app_label = "tests"

    with pytest.raises(ConfigError):

        class CategorySchema(ModelSchema):
            class Config:
                model = Category


def test_model_fields_all():
    class SomeModel(models.Model):
        field1 = models.CharField()
        field2 = models.CharField(blank=True, null=True)

        class Meta:
            app_label = "tests"

    class SomeSchema(ModelSchema):
        class Config:
            model = SomeModel
            model_fields = "__all__"

    print(SomeSchema.schema())
    assert SomeSchema.schema() == {
        "title": "SomeSchema",
        "type": "object",
        "properties": {
            "id": {"title": "Id", "type": "integer"},
            "field1": {"title": "Field1", "type": "string"},
            "field2": {"title": "Field2", "type": "string"},
        },
        "required": ["field1"],
    }


def test_model_schema_without_config():
    with pytest.raises(
        ConfigError,
        match="ModelSchema class 'NoConfigSchema' requires a 'Config' subclass",
    ):

        class NoConfigSchema(ModelSchema):
            pass
