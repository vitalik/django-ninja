from typing import List
from unittest.mock import Mock

import pytest
from django.contrib.postgres import fields as ps_fields
from django.db import models
from django.db.models import Manager
from util import pydantic_ref_fix

from ninja.errors import ConfigError
from ninja.orm import create_schema, register_field
from ninja.orm.shortcuts import L, S


def test_inheritance():
    class ParentModel(models.Model):
        parent_field = models.CharField()

        class Meta:
            app_label = "tests"

    class ChildModel(ParentModel):
        child_field = models.CharField()

        class Meta:
            app_label = "tests"

    Schema = create_schema(ChildModel)
    # print(Schema.json_schema())

    # TODO: I guess parentmodel_ptr_id must be skipped
    assert Schema.json_schema() == {
        "title": "ChildModel",
        "type": "object",
        "properties": {
            "id": {"anyOf": [{"type": "integer"}, {"type": "null"}], "title": "ID"},
            "parent_field": {"type": "string", "title": "Parent Field"},
            "parentmodel_ptr_id": {"type": "integer", "title": "Parentmodel Ptr"},
            "child_field": {"type": "string", "title": "Child Field"},
        },
        "required": ["parent_field", "parentmodel_ptr_id", "child_field"],
    }


def test_all_fields():
    # test all except relational field

    class AllFields(models.Model):
        bigintegerfield = models.BigIntegerField()
        binaryfield = models.BinaryField()
        booleanfield = models.BooleanField()
        charfield = models.CharField()
        commaseparatedintegerfield = models.CommaSeparatedIntegerField()
        datefield = models.DateField()
        datetimefield = models.DateTimeField()
        decimalfield = models.DecimalField()
        durationfield = models.DurationField()
        emailfield = models.EmailField()
        filefield = models.FileField()
        filepathfield = models.FilePathField()
        floatfield = models.FloatField()
        genericipaddressfield = models.GenericIPAddressField()
        ipaddressfield = models.IPAddressField()
        imagefield = models.ImageField()
        integerfield = models.IntegerField()
        nullbooleanfield = models.NullBooleanField()
        positiveintegerfield = models.PositiveIntegerField()
        positivesmallintegerfield = models.PositiveSmallIntegerField()
        slugfield = models.SlugField()
        smallintegerfield = models.SmallIntegerField()
        textfield = models.TextField()
        timefield = models.TimeField()
        urlfield = models.URLField()
        uuidfield = models.UUIDField()
        arrayfield = ps_fields.ArrayField(models.CharField())
        cicharfield = ps_fields.CICharField()
        ciemailfield = ps_fields.CIEmailField()
        citextfield = ps_fields.CITextField()
        hstorefield = ps_fields.HStoreField()

        class Meta:
            app_label = "tests"

    SchemaCls = create_schema(AllFields)
    # print(SchemaCls.json_schema())
    assert SchemaCls.json_schema() == {
        "title": "AllFields",
        "type": "object",
        "properties": {
            "id": {"anyOf": [{"type": "integer"}, {"type": "null"}], "title": "ID"},
            "bigintegerfield": {"title": "Bigintegerfield", "type": "integer"},
            "binaryfield": {
                "title": "Binaryfield",
                "type": "string",
                "format": "binary",
            },
            "booleanfield": {"type": "boolean", "title": "Booleanfield"},
            "charfield": {"type": "string", "title": "Charfield"},
            "commaseparatedintegerfield": {
                "title": "Commaseparatedintegerfield",
                "type": "string",
            },
            "datefield": {"type": "string", "format": "date", "title": "Datefield"},
            "datetimefield": {
                "title": "Datetimefield",
                "type": "string",
                "format": "date-time",
            },
            "decimalfield": {
                "anyOf": [{"type": "number"}, {"type": "string"}],
                "title": "Decimalfield",
            },
            "durationfield": {
                "type": "string",
                "format": "duration",
                "title": "Durationfield",
            },
            "emailfield": {"type": "string", "maxLength": 254, "title": "Emailfield"},
            "filefield": {"type": "string", "title": "Filefield"},
            "filepathfield": {"type": "string", "title": "Filepathfield"},
            "floatfield": {"type": "number", "title": "Floatfield"},
            "genericipaddressfield": {
                "type": "string",
                "format": "ipvanyaddress",
                "title": "Genericipaddressfield",
            },
            "ipaddressfield": {
                "type": "string",
                "format": "ipvanyaddress",
                "title": "Ipaddressfield",
            },
            "imagefield": {"type": "string", "title": "Imagefield"},
            "integerfield": {"type": "integer", "title": "Integerfield"},
            "nullbooleanfield": {"type": "boolean", "title": "Nullbooleanfield"},
            "positiveintegerfield": {
                "type": "integer",
                "title": "Positiveintegerfield",
            },
            "positivesmallintegerfield": {
                "type": "integer",
                "title": "Positivesmallintegerfield",
            },
            "slugfield": {"type": "string", "title": "Slugfield"},
            "smallintegerfield": {"type": "integer", "title": "Smallintegerfield"},
            "textfield": {"type": "string", "title": "Textfield"},
            "timefield": {"type": "string", "format": "time", "title": "Timefield"},
            "urlfield": {"type": "string", "title": "Urlfield"},
            "uuidfield": {"type": "string", "format": "uuid", "title": "Uuidfield"},
            "arrayfield": {"type": "array", "items": {}, "title": "Arrayfield"},
            "cicharfield": {"type": "string", "title": "Cicharfield"},
            "ciemailfield": {
                "type": "string",
                "maxLength": 254,
                "title": "Ciemailfield",
            },
            "citextfield": {"type": "string", "title": "Citextfield"},
            "hstorefield": {"type": "object", "title": "Hstorefield"},
        },
        "required": [
            "bigintegerfield",
            "binaryfield",
            "booleanfield",
            "charfield",
            "commaseparatedintegerfield",
            "datefield",
            "datetimefield",
            "decimalfield",
            "durationfield",
            "emailfield",
            "filefield",
            "filepathfield",
            "floatfield",
            "genericipaddressfield",
            "ipaddressfield",
            "imagefield",
            "integerfield",
            "nullbooleanfield",
            "positiveintegerfield",
            "positivesmallintegerfield",
            "slugfield",
            "smallintegerfield",
            "textfield",
            "timefield",
            "urlfield",
            "uuidfield",
            "arrayfield",
            "cicharfield",
            "ciemailfield",
            "citextfield",
            "hstorefield",
        ],
    }


@pytest.mark.parametrize(
    "field",
    [
        models.BigAutoField,
        models.SmallAutoField,
    ],
)
def test_altautofield(field: type):
    class ModelAltAuto(models.Model):
        altautofield = field(primary_key=True)

        class Meta:
            app_label = "tests"

    SchemaCls = create_schema(ModelAltAuto)
    # print(SchemaCls.json_schema())
    assert SchemaCls.json_schema()["properties"] == {
        "altautofield": {
            "anyOf": [{"type": "integer"}, {"type": "null"}],
            "title": "Altautofield",
        }
    }


def test_django_31_fields():
    class ModelNewFields(models.Model):
        jsonfield = models.JSONField()
        positivebigintegerfield = models.PositiveBigIntegerField()

        class Meta:
            app_label = "tests"

    Schema = create_schema(ModelNewFields)
    # print(Schema.json_schema())
    assert Schema.json_schema() == {
        "title": "ModelNewFields",
        "type": "object",
        "properties": {
            "id": {"title": "ID", "anyOf": [{"type": "integer"}, {"type": "null"}]},
            "jsonfield": {"title": "Jsonfield", "type": "object"},
            "positivebigintegerfield": {
                "title": "Positivebigintegerfield",
                "type": "integer",
            },
        },
        "required": ["jsonfield", "positivebigintegerfield"],
    }

    obj = Schema(id=1, jsonfield={"any": "data"}, positivebigintegerfield=1)
    assert obj.dict() == {
        "id": 1,
        "jsonfield": {"any": "data"},
        "positivebigintegerfield": 1,
    }


def test_relational():
    class Related(models.Model):
        charfield = models.CharField()

        class Meta:
            app_label = "tests"

    class TestModel(models.Model):
        manytomanyfield = models.ManyToManyField(Related)
        onetoonefield = models.OneToOneField(Related, on_delete=models.CASCADE)
        foreignkey = models.ForeignKey(Related, on_delete=models.SET_NULL, null=True)

        class Meta:
            app_label = "tests"

    SchemaCls = create_schema(TestModel, name="TestSchema")
    # print(SchemaCls.json_schema())
    assert SchemaCls.json_schema() == {
        "title": "TestSchema",
        "type": "object",
        "properties": {
            "id": {"anyOf": [{"type": "integer"}, {"type": "null"}], "title": "ID"},
            "onetoonefield_id": {"title": "Onetoonefield", "type": "integer"},
            "foreignkey_id": {
                "anyOf": [{"type": "integer"}, {"type": "null"}],
                "title": "Foreignkey",
            },
            "manytomanyfield": {
                "title": "Manytomanyfield",
                "type": "array",
                "items": {"type": "integer"},
            },
        },
        "required": ["onetoonefield_id", "manytomanyfield"],
    }

    SchemaClsDeep = create_schema(TestModel, name="TestSchemaDeep", depth=1)
    print(SchemaClsDeep.json_schema())
    assert SchemaClsDeep.json_schema() == {
        "type": "object",
        "properties": {
            "id": {"anyOf": [{"type": "integer"}, {"type": "null"}], "title": "ID"},
            "onetoonefield": pydantic_ref_fix({
                "title": "Onetoonefield",
                "description": "",
                "$ref": "#/$defs/Related",
            }),
            "foreignkey": {
                "title": "Foreignkey",
                "allOf": [{"$ref": "#/$defs/Related"}],
                "description": "",
            },
            "manytomanyfield": {
                "title": "Manytomanyfield",
                "type": "array",
                "items": {"$ref": "#/$defs/Related"},
                "description": "",
            },
        },
        "required": ["onetoonefield", "manytomanyfield"],
        "title": "TestSchemaDeep",
        "$defs": {
            "Related": {
                "title": "Related",
                "type": "object",
                "properties": {
                    "id": {
                        "anyOf": [{"type": "integer"}, {"type": "null"}],
                        "title": "ID",
                    },
                    "charfield": {"type": "string", "title": "Charfield"},
                },
                "required": ["charfield"],
            }
        },
    }


def test_default():
    class MyModel(models.Model):
        default_static = models.CharField(default="hello")
        default_dynamic = models.CharField(default=lambda: "world")

        class Meta:
            app_label = "tests"

    Schema = create_schema(MyModel)
    # print(Schema.json_schema())
    assert Schema.json_schema() == {
        "title": "MyModel",
        "type": "object",
        "properties": {
            "id": {"anyOf": [{"type": "integer"}, {"type": "null"}], "title": "ID"},
            "default_static": {
                "default": "hello",
                "title": "Default Static",
                "type": "string",
            },
            "default_dynamic": {"title": "Default Dynamic", "type": "string"},
        },
    }


def test_fields_exclude():
    class SampleModel(models.Model):
        f1 = models.CharField()
        f2 = models.CharField()
        f3 = models.CharField()

        class Meta:
            app_label = "tests"

    Schema1 = create_schema(SampleModel, fields=["f1", "f2"])
    # print(Schema1.json_schema())
    assert Schema1.json_schema() == {
        "title": "SampleModel",
        "type": "object",
        "properties": {
            "f1": {"type": "string", "title": "F1"},
            "f2": {"type": "string", "title": "F2"},
        },
        "required": ["f1", "f2"],
    }

    Schema2 = create_schema(SampleModel, fields=["f3", "f2"])
    # print(Schema2.json_schema())
    assert Schema2.json_schema() == {
        "title": "SampleModel2",
        "type": "object",
        "properties": {
            "f3": {"title": "F3", "type": "string"},
            "f2": {"title": "F2", "type": "string"},
        },
        "required": ["f3", "f2"],
    }

    Schema3 = create_schema(SampleModel, exclude=["f3"])
    # print(Schema3.json_schema())
    assert Schema3.json_schema() == {
        "type": "object",
        "properties": {
            "id": {"anyOf": [{"type": "integer"}, {"type": "null"}], "title": "ID"},
            "f1": {"type": "string", "title": "F1"},
            "f2": {"type": "string", "title": "F2"},
        },
        "required": ["f1", "f2"],
        "title": "SampleModel3",
    }


def test_exceptions():
    class MyModel2(models.Model):
        f1 = models.CharField()
        f2 = models.CharField()

        class Meta:
            app_label = "tests"

    with pytest.raises(
        ConfigError, match="Only one of 'fields' or 'exclude' should be set."
    ):
        create_schema(MyModel2, fields=["f1"], exclude=["f2"])

    with pytest.raises(ConfigError):
        create_schema(MyModel2, fields=["f_invalid"])


def test_shortcuts():
    class MyModel3(models.Model):
        f1 = models.CharField()

        class Meta:
            app_label = "tests"

    schema = S(MyModel3)
    schema_list = L(MyModel3)
    assert List[schema] == schema_list


@pytest.mark.django_db
def test_with_relations():
    # this test basically does full coverage for the case when we skip automatic relation attributes
    from someapp.models import Category

    Schema = create_schema(Category)
    # print(Schema.json_schema())
    assert Schema.json_schema() == {
        "title": "Category",
        "type": "object",
        "properties": {
            "id": {"anyOf": [{"type": "integer"}, {"type": "null"}], "title": "ID"},
            "title": {"title": "Title", "maxLength": 100, "type": "string"},
        },
        "required": ["title"],
    }


def test_manytomany():
    class Foo(models.Model):
        f = models.CharField()

        class Meta:
            app_label = "tests"

    class Bar(models.Model):
        m2m = models.ManyToManyField(Foo, blank=True)

        class Meta:
            app_label = "tests"

    Schema = create_schema(Bar)

    # mocking database data:

    foo = Mock()
    foo.pk = 1
    foo.f = "test"

    m2m = Mock(spec=Manager)
    m2m.all = lambda: [foo]

    bar = Mock()
    bar.id = 1
    bar.m2m = m2m

    data = Schema.from_orm(bar).dict()

    assert data == {"id": 1, "m2m": [1]}


def test_custom_fields():
    class SmallModel(models.Model):
        f1 = models.CharField()
        f2 = models.CharField()

        class Meta:
            app_label = "tests"

    Schema1 = create_schema(SmallModel, custom_fields=[("custom", int, ...)])

    # print(Schema1.json_schema())
    assert Schema1.json_schema() == {
        "type": "object",
        "properties": {
            "id": {"anyOf": [{"type": "integer"}, {"type": "null"}], "title": "ID"},
            "f1": {"type": "string", "title": "F1"},
            "f2": {"type": "string", "title": "F2"},
            "custom": {"type": "integer", "title": "Custom"},
        },
        "required": ["f1", "f2", "custom"],
        "title": "SmallModel",
    }

    Schema2 = create_schema(SmallModel, custom_fields=[("f1", int, ...)])
    # print(Schema2.json_schema())

    assert Schema2.json_schema() == {
        "type": "object",
        "properties": {
            "id": {"anyOf": [{"type": "integer"}, {"type": "null"}], "title": "ID"},
            "f1": {"type": "integer", "title": "F1"},
            "f2": {"type": "string", "title": "F2"},
        },
        "required": ["f1", "f2"],
        "title": "SmallModel2",
    }


def test_duplicate_schema_names():
    from django.db import models

    from ninja import Schema
    from ninja.orm import create_schema

    class TestModelDuplicate(models.Model):
        field1 = models.CharField()
        field2 = models.CharField()

        class Meta:
            app_label = "tests"

    class TestSchema(Schema):
        data1: create_schema(TestModelDuplicate, fields=["field1"])  # noqa: F821
        data2: create_schema(TestModelDuplicate, fields=["field2"])  # noqa: F821

    # print(TestSchema.json_schema())

    assert TestSchema.json_schema() == {
        "type": "object",
        "properties": {
            "data1": {"$ref": "#/$defs/TestModelDuplicate"},
            "data2": {"$ref": "#/$defs/TestModelDuplicate2"},
        },
        "required": ["data1", "data2"],
        "title": "TestSchema",
        "$defs": {
            "TestModelDuplicate": {
                "type": "object",
                "properties": {"field1": {"type": "string", "title": "Field1"}},
                "required": ["field1"],
                "title": "TestModelDuplicate",
            },
            "TestModelDuplicate2": {
                "type": "object",
                "properties": {"field2": {"type": "string", "title": "Field2"}},
                "required": ["field2"],
                "title": "TestModelDuplicate2",
            },
        },
    }


def test_optional_fields():
    class SomeReqFieldModel(models.Model):
        some_field = models.CharField()
        other_field = models.IntegerField()
        optional = models.IntegerField(null=True, blank=True)

        class Meta:
            app_label = "tests"

    Schema = create_schema(SomeReqFieldModel)
    assert Schema.json_schema()["required"] == ["some_field", "other_field"]

    Schema = create_schema(SomeReqFieldModel, optional_fields=["some_field"])
    assert Schema.json_schema()["required"] == ["other_field"]

    Schema = create_schema(
        SomeReqFieldModel, optional_fields=["some_field", "other_field", "optional"]
    )
    assert Schema.json_schema().get("required") is None


def test_register_custom_field():
    class MyCustomField(models.Field):
        description = "MyCustomField"

    class ModelWithCustomField(models.Model):
        some_field = MyCustomField()

        class Meta:
            app_label = "tests"

    with pytest.raises(ConfigError):
        create_schema(ModelWithCustomField)

    register_field("MyCustomField", int)
    Schema = create_schema(ModelWithCustomField)
    print(Schema.json_schema())
    assert Schema.json_schema()["properties"]["some_field"]["type"] == "integer"
