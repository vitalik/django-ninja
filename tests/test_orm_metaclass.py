import warnings

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
        "required": ["f1", "f3"],
    }


def test_custom_fields_come_after_model_fields():
    class OrderModel(models.Model):
        name = models.CharField()
        created = models.DateTimeField(null=True)

        class Meta:
            app_label = "tests"

    class OrderSchema(ModelSchema):
        extra_a: int
        extra_b: str = "b"

        class Meta:
            model = OrderModel
            fields = ["name", "id"]

    # model fields keep the order given in Meta.fields,
    # custom fields follow in declaration order
    assert list(OrderSchema.model_fields) == ["name", "id", "extra_a", "extra_b"]
    assert list(OrderSchema.json_schema()["properties"]) == [
        "name",
        "id",
        "extra_a",
        "extra_b",
    ]

    instance = OrderSchema(name="n", id=7, extra_a=1)
    assert list(instance.model_dump()) == ["name", "id", "extra_a", "extra_b"]
    assert instance.model_dump_json() == (
        '{"name":"n","id":7,"extra_a":1,"extra_b":"b"}'
    )


def test_custom_field_overriding_model_field():
    class OverrideModel(models.Model):
        name = models.CharField()
        rating = models.IntegerField()

        class Meta:
            app_label = "tests"

    class OverrideSchema(ModelSchema):
        # redefines the model field with a different type/default
        rating: float = 0.5
        extra: int = 0

        class Meta:
            model = OverrideModel
            fields = ["name"]

    assert list(OverrideSchema.model_fields) == ["name", "rating", "extra"]
    assert OverrideSchema.model_fields["rating"].annotation is float
    assert OverrideSchema(name="n").rating == 0.5


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


def test_model_as_string_valid():
    class SomeModel(models.Model):
        field1 = models.CharField()

        class Meta:
            app_label = "someapp"

    class SomeStringModelSchema(ModelSchema):
        class Meta:
            model = "someapp.SomeModel"
            fields = ["field1"]

    assert SomeStringModelSchema.json_schema() == {
        "title": "SomeStringModelSchema",
        "type": "object",
        "properties": {"field1": {"title": "Field1", "type": "string"}},
        "required": ["field1"],
    }


def test_model_as_string_invalid_format():
    with pytest.raises(
        ValueError,
        match="Model string must be in format 'app_label.ModelName', got: SomeModel",
    ):

        class SomeSchema(ModelSchema):
            class Meta:
                model = "SomeModel"
                fields = ["field1"]


def test_model_as_string_invalid_format2():
    with pytest.raises(
        ValueError,
        match="Model string must be in format 'app_label.ModelName', got: someapp.models.SomeModel",
    ):

        class SomeSchema(ModelSchema):
            class Meta:
                model = "someapp.models.SomeModel"
                fields = ["field1"]


def test_model_as_string_nonexistent_app():
    with pytest.raises(
        LookupError,
        match="No installed app with label 'nonexistentapp'.",
    ):

        class SomeSchema(ModelSchema):
            class Meta:
                model = "nonexistentapp.NonExistentModel"
                fields = ["field1"]


def test_model_as_string_nonexistent_model_in_app():
    with pytest.raises(
        LookupError,
        match="App 'someapp' doesn't have a 'NonExistentModel' model.",
    ):

        class SomeSchema(ModelSchema):
            class Meta:
                model = "someapp.NonExistentModel"
                fields = ["field1"]


def test_model_schema_without_meta():
    with pytest.raises(
        ConfigError,
        match=r"ModelSchema class 'NoMetaSchema' requires a 'Meta' subclass",
    ):

        class NoMetaSchema(ModelSchema):
            x: int


def test_model_schema_with_old_config():
    with pytest.raises(
        ConfigError,
        match=r"The use of `Config` class is removed for ModelSchema, use 'Meta' instead",
    ):

        class OldConfigSchema(ModelSchema):
            x: int

            class Config:
                model = "User"
                model_fields = ["x"]


def test_same_named_model_schemas_keep_their_own_body():
    class CacheKeyPub(models.Model):
        name = models.CharField(max_length=5)

        class Meta:
            app_label = "tests"

    def make(value):
        class CacheKeyPubSchema(ModelSchema):
            class Meta:
                model = CacheKeyPub
                fields = ["id"]

            @staticmethod
            def resolve_id(obj):
                return value

        return CacheKeyPubSchema

    first, second = make(1), make(2)

    assert first is not second
    assert first.__name__ != second.__name__
    assert first.model_validate(CacheKeyPub(id=5)).id == 1
    assert second.model_validate(CacheKeyPub(id=5)).id == 2


def test_declared_field_also_in_fields_warns():
    """#1563: a declared field repeated in Meta.fields - the declaration wins, with a warning."""

    class Author(models.Model):
        name = models.CharField()

        class Meta:
            app_label = "tests"

    class Tip(models.Model):
        name = models.CharField()
        author = models.ForeignKey(Author, on_delete=models.CASCADE)

        class Meta:
            app_label = "tests"

    class AuthorSchema(ModelSchema):
        class Meta:
            model = Author
            fields = ["id", "name"]

    with pytest.warns(
        DeprecationWarning, match=r"'TipSchema' declares field\(s\) \['author'\]"
    ):

        class TipSchema(ModelSchema):
            author: AuthorSchema

            class Meta:
                model = Tip
                fields = ["id", "name", "author"]

    properties = TipSchema.json_schema()["properties"]
    assert set(properties) == {"id", "name", "author"}
    assert properties["author"] == {"$ref": "#/$defs/AuthorSchema"}


def test_declared_field_not_repeated_in_fields_does_not_warn():
    class Note(models.Model):
        title = models.CharField()
        body = models.CharField()

        class Meta:
            app_label = "tests"

    with warnings.catch_warnings():
        warnings.simplefilter("error")

        class NoteSchema(ModelSchema):
            title: int

            class Meta:
                model = Note
                fields = ["body"]

        class NoteSchemaAll(ModelSchema):
            title: int

            class Meta:
                model = Note
                fields = "__all__"

    for schema in (NoteSchema, NoteSchemaAll):
        properties = schema.json_schema()["properties"]
        assert properties["title"] == {"title": "Title", "type": "integer"}
        assert properties["body"] == {"title": "Body", "type": "string"}
