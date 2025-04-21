from typing import Annotated, Optional, TypeVar

import pytest
from django.db import models
from pydantic import GetJsonSchemaHandler, ValidationError, model_serializer
from pydantic.json_schema import JsonSchemaValue
from pydantic_core import core_schema

from ninja import ModelSchema, Schema
from ninja.errors import ConfigError


def test_simple():
    class User(models.Model):
        firstname = models.CharField()
        lastname = models.CharField(blank=True, null=True)

        class Meta:
            app_label = "tests"

    class SampleSchema(ModelSchema):
        class Meta:
            model = User
            fields = ["firstname", "lastname"]

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

    with pytest.raises(ConfigError, match="Specify either `exclude` or `fields`"):

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


def test_nondjango_model_error():
    class NonDjangoModel:
        field1 = models.CharField()
        field2 = models.CharField(blank=True, null=True)

    with pytest.raises(
        ValidationError,
        match=r"Input should be a subclass of Model \[type=is_subclass_of, input_value=<class 'test_orm_metaclas...locals>.NonDjangoModel'>, input_type=type\]",
    ):

        class SomeSchema(ModelSchema):
            class Meta:
                model = NonDjangoModel
                fields = "__all__"


class OmissibleClass:
    """
    Class for the custom Omissible type to modify the JsonSchemaValue for the field.
    """

    @classmethod
    def __get_pydantic_json_schema__(
        cls, source: core_schema.CoreSchema, handler: GetJsonSchemaHandler
    ) -> JsonSchemaValue:
        output = handler(source)
        # FIXME: access by static index
        t_type = output["anyOf"][0]
        del output["anyOf"]

        assert any(i in t_type.keys() for i in ["type", "$ref"])

        for key in ["type", "$ref"]:
            val = t_type.get(key)
            if val is not None:
                output[key] = val
                break
        return output


T = TypeVar("T")
Omissible = Annotated[Optional[T], OmissibleClass]


def _omissible_serialize(self, handler):
    """Delete the key from the dump if the key is Omissible and None"""
    dump = handler(self)
    for key, field_info in self.model_fields.items():
        metadata = field_info.metadata
        for c in metadata:
            if dump.get(key) is None and OmissibleClass == c:
                del dump[key]

    return dump


def test_better_inheritance():
    class SomeModel(models.Model):
        field1 = models.CharField()
        field2 = models.CharField(blank=True, null=True)

        class Meta:
            app_label = "tests"

    class ProjectBaseSchema(Schema):
        _omissible_serialize = model_serializer(mode="wrap")(_omissible_serialize)

    class ProjectBaseModelSchema(ModelSchema, ProjectBaseSchema):
        # more pydantic modelschema options
        class Meta:
            primary_key_optional = False

    with pytest.raises(
        ConfigError,
        match="No model set for class 'ProjectBaseModelSchema' in the Meta hierarchy",
    ):
        ProjectBaseModelSchema()

    class Intermediate(ProjectBaseModelSchema):
        class Meta:
            depth = 0

    with pytest.raises(
        ConfigError,
        match="No model set for class 'Intermediate' in the Meta hierarchy",
    ):
        Intermediate()

    class SomeModelSchema(ProjectBaseModelSchema):
        field2: Omissible[str] = None
        extra: Omissible[str] = None

        class Meta:
            model = SomeModel
            fields = "__all__"

    assert SomeModelSchema._omissible_serialize
    assert not getattr(SomeModelSchema, "Meta", None)
    assert SomeModelSchema.__ninja_meta__["model"] == SomeModel
    assert SomeModelSchema.__ninja_meta__["fields"] == "__all__"
    assert not SomeModelSchema.__ninja_meta__["primary_key_optional"]

    assert len(SomeModelSchema.__annotations__.keys()) == 4
    assert SomeModelSchema.__annotations__["id"] == int
    assert SomeModelSchema.__annotations__["field2"] == Omissible[str]
    assert SomeModelSchema.__annotations__["extra"] == Omissible[str]
    assert SomeModelSchema.__annotations__["field1"] == str

    sms = SomeModelSchema(id=1, field1="char", field2="opt")
    assert sms.json() == '{"field2":"opt","id":1,"field1":"char"}'
    assert sms.json_schema() == {
        "properties": {
            "field2": {
                "title": "Field2",
                "type": "string",
            },
            "extra": {
                "title": "Extra",
                "type": "string",
            },
            "id": {
                "title": "ID",
                "type": "integer",
            },
            "field1": {
                "title": "Field1",
                "type": "string",
            },
        },
        "required": [
            "id",
            "field1",
        ],
        "title": "SomeModelSchema",
        "type": "object",
    }
