from typing import Optional

import pytest
from django.db import models
from pydantic import BaseModel, ValidationError

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

    with pytest.raises(ValidationError, match="Specify either `exclude` or `fields`"):

        class CategorySchema1(ModelSchema):
            class Meta:
                model = Category

    with pytest.raises(ValidationError, match="Specify either `exclude` or `fields`"):

        class CategorySchema2(ModelSchema):
            class Meta:
                model = Category
                exclude = ["title"]
                fields = ["title"]

    with pytest.raises(
        ValidationError,
        match="Use only `optional_fields`, `fields_optional` is deprecated.",
    ):

        class CategorySchema3(ModelSchema):
            class Meta:
                model = Category
                fields = "__all__"
                fields_optional = ["title"]
                optional_fields = ["title"]

    with pytest.raises(
        ConfigError,
        match="'title' is defined in class body and in Meta.fields or implicitly in Meta.excluded",
    ):

        class CategorySchema4(ModelSchema):
            title: str

            class Meta:
                model = Category
                fields = "__all__"

    class CategorySchema5(ModelSchema):
        class Config:
            model = Category
            fields = "__all__"


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
    # do not raise on creation of class
    class NoConfigSchema(ModelSchema):
        x: int

    with pytest.raises(
        ConfigError,
        match=r"No model set for class 'NoConfigSchema'",
    ):
        NoConfigSchema(x=1)


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


def test_desired_inheritance():
    class Item(models.Model):
        id = models.PositiveIntegerField(primary_key=True)
        slug = models.CharField()

        class Meta:
            app_label = "tests"

    class ProjectBaseSchema(Schema):
        # add any project wide Schema/pydantic configs
        _omissible_serialize = (
            "serializer_func"  # model_serializer(mode="wrap")(_omissible_serialize)
        )

    class ProjectBaseModelSchema(ModelSchema, ProjectBaseSchema):
        _pydantic_config = "config"

        class Meta:
            primary_key_optional = False

    class ResourceModelSchema(ProjectBaseModelSchema):
        field1: str

        class Meta(ProjectBaseModelSchema.Meta):
            model = Item
            fields = ["id"]

    class ItemModelSchema(ResourceModelSchema):
        field2: str

        class Meta(ResourceModelSchema.Meta):
            model = Item
            fields = ["id", "slug"]

    assert issubclass(ItemModelSchema, BaseModel)
    assert ItemModelSchema.Meta.primary_key_optional is False

    i = ItemModelSchema(id=1, slug="slug", field1="1", field2="2")

    assert i._pydantic_config == "config"
    assert i._omissible_serialize == "serializer_func"
    assert i.model_dump_json() == '{"field1":"1","id":1,"field2":"2","slug":"slug"}'
    assert i.model_json_schema() == {
        "properties": {
            "field1": {
                "title": "Field1",
                "type": "string",
            },
            "id": {
                "type": "integer",
                "title": "Id",
            },
            "field2": {
                "title": "Field2",
                "type": "string",
            },
            "slug": {
                "title": "Slug",
                "type": "string",
            },
        },
        "required": [
            "field1",
            "id",
            "field2",
            "slug",
        ],
        "title": "ItemModelSchema",
        "type": "object",
    }


def test_specific_inheritance():
    """https://github.com/vitalik/django-ninja/issues/347"""

    class Item(models.Model):
        id = models.PositiveIntegerField
        slug = models.CharField()
        name = models.CharField()
        image_path = models.CharField()
        length_in_mn = models.PositiveIntegerField()
        special_field_for_meal = models.CharField()

        class Meta:
            app_label = "tests"

    class ItemBaseModelSchema(ModelSchema):
        is_favorite: Optional[bool] = None

        class Meta:
            model = Item
            fields = [
                "id",
                "slug",
                "name",
                "image_path",
            ]

    class ItemInBasesSchema(ItemBaseModelSchema):
        class Meta(ItemBaseModelSchema.Meta):
            model = Item
            fields = ItemBaseModelSchema.Meta.fields + ["length_in_mn"]

    class ItemInMealsSchema(ItemBaseModelSchema):
        class Meta(ItemBaseModelSchema.Meta):
            model = Item
            fields = ItemBaseModelSchema.Meta.fields + [
                "length_in_mn",
                "special_field_for_meal",
            ]

    ibase = ItemBaseModelSchema(
        id=1,
        slug="slug",
        name="item",
        image_path="/images/image.png",
        is_favorite=False,
    )
    item_inbases = ItemInBasesSchema(
        id=2,
        slug="slug",
        name="item",
        image_path="/images/image.png",
        is_favorite=False,
        length_in_mn=2,
    )
    item_inmeals = ItemInMealsSchema(
        id=3,
        slug="slug",
        name="item",
        image_path="/images/image.png",
        is_favorite=False,
        length_in_mn=2,
        special_field_for_meal="char",
    )

    assert (
        ibase.model_dump_json()
        == '{"is_favorite":false,"id":1,"slug":"slug","name":"item","image_path":"/images/image.png"}'
    )
    assert ibase.model_json_schema() == {
        "properties": {
            "is_favorite": {
                "anyOf": [
                    {
                        "type": "boolean",
                    },
                    {
                        "type": "null",
                    },
                ],
                "default": None,
                "title": "Is Favorite",
            },
            "id": {
                "anyOf": [
                    {
                        "type": "integer",
                    },
                    {
                        "type": "null",
                    },
                ],
                "default": None,
                "title": "ID",
            },
            "slug": {
                "title": "Slug",
                "type": "string",
            },
            "name": {
                "title": "Name",
                "type": "string",
            },
            "image_path": {
                "title": "Image Path",
                "type": "string",
            },
        },
        "required": [
            "slug",
            "name",
            "image_path",
        ],
        "title": "ItemBaseModelSchema",
        "type": "object",
    }

    assert (
        item_inbases.model_dump_json()
        == '{"is_favorite":false,"id":2,"slug":"slug","name":"item","image_path":"/images/image.png","length_in_mn":2}'
    )
    assert item_inbases.model_json_schema() == {
        "properties": {
            "is_favorite": {
                "anyOf": [
                    {
                        "type": "boolean",
                    },
                    {
                        "type": "null",
                    },
                ],
                "default": None,
                "title": "Is Favorite",
            },
            "id": {
                "anyOf": [
                    {
                        "type": "integer",
                    },
                    {
                        "type": "null",
                    },
                ],
                "default": None,
                "title": "ID",
            },
            "slug": {
                "title": "Slug",
                "type": "string",
            },
            "name": {
                "title": "Name",
                "type": "string",
            },
            "image_path": {
                "title": "Image Path",
                "type": "string",
            },
            "length_in_mn": {
                "title": "Length In Mn",
                "type": "integer",
            },
        },
        "required": [
            "slug",
            "name",
            "image_path",
            "length_in_mn",
        ],
        "title": "ItemInBasesSchema",
        "type": "object",
    }

    assert (
        item_inmeals.model_dump_json()
        == '{"is_favorite":false,"id":3,"slug":"slug","name":"item","image_path":"/images/image.png","length_in_mn":2,"special_field_for_meal":"char"}'
    )
    assert item_inmeals.model_json_schema() == {
        "properties": {
            "is_favorite": {
                "anyOf": [
                    {
                        "type": "boolean",
                    },
                    {
                        "type": "null",
                    },
                ],
                "default": None,
                "title": "Is Favorite",
            },
            "id": {
                "anyOf": [
                    {
                        "type": "integer",
                    },
                    {
                        "type": "null",
                    },
                ],
                "default": None,
                "title": "ID",
            },
            "slug": {
                "title": "Slug",
                "type": "string",
            },
            "name": {
                "title": "Name",
                "type": "string",
            },
            "image_path": {
                "title": "Image Path",
                "type": "string",
            },
            "length_in_mn": {
                "title": "Length In Mn",
                "type": "integer",
            },
            "special_field_for_meal": {
                "title": "Special Field For Meal",
                "type": "string",
            },
        },
        "required": [
            "slug",
            "name",
            "image_path",
            "length_in_mn",
            "special_field_for_meal",
        ],
        "title": "ItemInMealsSchema",
        "type": "object",
    }
