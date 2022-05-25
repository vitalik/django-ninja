from typing import List
from unittest.mock import Mock

import django
import pytest
from django.contrib.postgres import fields as ps_fields
from django.db import models
from django.db.models import Manager

from ninja.errors import ConfigError
from ninja.orm import create_schema
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
    print(Schema.schema())

    # TODO: I guess parentmodel_ptr_id must be skipped
    assert Schema.schema() == {
        "title": "ChildModel",
        "type": "object",
        "properties": {
            "id": {"title": "Id", "type": "integer"},
            "parent_field": {"title": "Parent Field", "type": "string"},
            "parentmodel_ptr_id": {"title": "Parentmodel Ptr", "type": "integer"},
            "child_field": {"title": "Child Field", "type": "string"},
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
    print(SchemaCls.schema())
    assert SchemaCls.schema() == {
        "title": "AllFields",
        "type": "object",
        "properties": {
            "id": {"title": "Id", "type": "integer"},
            "bigintegerfield": {"title": "Bigintegerfield", "type": "integer"},
            "binaryfield": {
                "title": "Binaryfield",
                "type": "string",
                "format": "binary",
            },
            "booleanfield": {"title": "Booleanfield", "type": "boolean"},
            "charfield": {"title": "Charfield", "type": "string"},
            "commaseparatedintegerfield": {
                "title": "Commaseparatedintegerfield",
                "type": "string",
            },
            "datefield": {"title": "Datefield", "type": "string", "format": "date"},
            "datetimefield": {
                "title": "Datetimefield",
                "type": "string",
                "format": "date-time",
            },
            "decimalfield": {"title": "Decimalfield", "type": "number"},
            "durationfield": {
                "title": "Durationfield",
                "type": "number",
                "format": "time-delta",
            },
            "emailfield": {"title": "Emailfield", "maxLength": 254, "type": "string"},
            "filefield": {"title": "Filefield", "type": "string"},
            "filepathfield": {"title": "Filepathfield", "type": "string"},
            "floatfield": {"title": "Floatfield", "type": "number"},
            "genericipaddressfield": {
                "title": "Genericipaddressfield",
                "type": "string",
                "format": "ipvanyaddress",
            },
            "ipaddressfield": {
                "title": "Ipaddressfield",
                "type": "string",
                "format": "ipvanyaddress",
            },
            "imagefield": {"title": "Imagefield", "type": "string"},
            "integerfield": {"title": "Integerfield", "type": "integer"},
            "nullbooleanfield": {"title": "Nullbooleanfield", "type": "boolean"},
            "positiveintegerfield": {
                "title": "Positiveintegerfield",
                "type": "integer",
            },
            "positivesmallintegerfield": {
                "title": "Positivesmallintegerfield",
                "type": "integer",
            },
            "slugfield": {"title": "Slugfield", "type": "string"},
            "smallintegerfield": {"title": "Smallintegerfield", "type": "integer"},
            "textfield": {"title": "Textfield", "type": "string"},
            "timefield": {"title": "Timefield", "type": "string", "format": "time"},
            "urlfield": {"title": "Urlfield", "type": "string"},
            "uuidfield": {"title": "Uuidfield", "type": "string", "format": "uuid"},
            "arrayfield": {"title": "Arrayfield", "type": "array", "items": {}},
            "cicharfield": {"title": "Cicharfield", "type": "string"},
            "ciemailfield": {
                "title": "Ciemailfield",
                "maxLength": 254,
                "type": "string",
            },
            "citextfield": {"title": "Citextfield", "type": "string"},
            "hstorefield": {"title": "Hstorefield", "type": "object"},
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


def test_bigautofield():
    class ModelBigAuto(models.Model):
        bigautofiled = models.BigAutoField(primary_key=True)

        class Meta:
            app_label = "tests"

    SchemaCls = create_schema(ModelBigAuto)
    print(SchemaCls.schema())
    assert SchemaCls.schema() == {
        "title": "ModelBigAuto",
        "type": "object",
        "properties": {"bigautofiled": {"title": "Bigautofiled", "type": "integer"}},
    }


@pytest.mark.skipif(
    django.VERSION < (3, 1), reason="json field introduced in django 3.1"
)
def test_django_31_fields():
    class ModelNewFields(models.Model):
        jsonfield = models.JSONField()
        positivebigintegerfield = models.PositiveBigIntegerField()

        class Meta:
            app_label = "tests"

    Schema = create_schema(ModelNewFields)
    print(Schema.schema())
    assert Schema.schema() == {
        "title": "ModelNewFields",
        "type": "object",
        "properties": {
            "id": {"title": "Id", "type": "integer"},
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
    print(SchemaCls.schema())
    assert SchemaCls.schema() == {
        "title": "TestSchema",
        "type": "object",
        "properties": {
            "id": {"title": "Id", "type": "integer"},
            "onetoonefield_id": {"title": "Onetoonefield", "type": "integer"},
            "foreignkey_id": {"title": "Foreignkey", "type": "integer"},
            "manytomanyfield": {
                "title": "Manytomanyfield",
                "type": "array",
                "items": {"type": "integer"},
            },
        },
        "required": ["onetoonefield_id", "manytomanyfield"],
    }

    SchemaClsDeep = create_schema(TestModel, name="TestSchemaDeep", depth=1)
    print(SchemaClsDeep.schema())
    assert SchemaClsDeep.schema() == {
        "title": "TestSchemaDeep",
        "type": "object",
        "properties": {
            "id": {"title": "Id", "type": "integer"},
            "onetoonefield": {
                "title": "Onetoonefield",
                "allOf": [{"$ref": "#/definitions/Related"}],
            },
            "foreignkey": {
                "title": "Foreignkey",
                "allOf": [{"$ref": "#/definitions/Related"}],
            },
            "manytomanyfield": {
                "title": "Manytomanyfield",
                "type": "array",
                "items": {"$ref": "#/definitions/Related"},
            },
        },
        "required": ["onetoonefield", "manytomanyfield"],
        "definitions": {
            "Related": {
                "title": "Related",
                "type": "object",
                "properties": {
                    "id": {"title": "Id", "type": "integer"},
                    "charfield": {"title": "Charfield", "type": "string"},
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
    print(Schema.schema())
    assert Schema.schema() == {
        "title": "MyModel",
        "type": "object",
        "properties": {
            "id": {"title": "Id", "type": "integer"},
            "default_static": {
                "title": "Default Static",
                "default": "hello",
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
    print(Schema1.schema())
    assert Schema1.schema() == {
        "title": "SampleModel",
        "type": "object",
        "properties": {
            "f1": {"title": "F1", "type": "string"},
            "f2": {"title": "F2", "type": "string"},
        },
        "required": ["f1", "f2"],
    }

    Schema2 = create_schema(SampleModel, fields=["f3", "f2"])
    print(Schema2.schema())
    assert Schema2.schema() == {
        "title": "SampleModel2",
        "type": "object",
        "properties": {
            "f3": {"title": "F3", "type": "string"},
            "f2": {"title": "F2", "type": "string"},
        },
        "required": ["f3", "f2"],
    }

    Schema3 = create_schema(SampleModel, exclude=["f3"])
    print(Schema3.schema())
    assert Schema3.schema() == {
        "title": "SampleModel3",
        "type": "object",
        "properties": {
            "id": {"title": "Id", "type": "integer"},
            "f1": {"title": "F1", "type": "string"},
            "f2": {"title": "F2", "type": "string"},
        },
        "required": ["f1", "f2"],
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
    print(Schema.schema())
    assert Schema.schema() == {
        "title": "Category",
        "type": "object",
        "properties": {
            "id": {"title": "Id", "type": "integer"},
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

    assert Schema1.schema() == {
        "title": "SmallModel",
        "type": "object",
        "properties": {
            "id": {"title": "Id", "type": "integer"},
            "f1": {"title": "F1", "type": "string"},
            "f2": {"title": "F2", "type": "string"},
            "custom": {"title": "Custom", "type": "integer"},
        },
        "required": ["f1", "f2", "custom"],
    }

    Schema2 = create_schema(SmallModel, custom_fields=[("f1", int, ...)])
    print(Schema2.schema())

    assert Schema2.schema() == {
        "title": "SmallModel2",
        "type": "object",
        "properties": {
            "id": {"title": "Id", "type": "integer"},
            "f1": {"title": "F1", "type": "integer"},
            "f2": {"title": "F2", "type": "string"},
        },
        "required": ["f1", "f2"],
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

    print(TestSchema.schema())

    assert TestSchema.schema() == {
        "title": "TestSchema",
        "type": "object",
        "properties": {
            "data1": {"$ref": "#/definitions/TestModelDuplicate"},
            "data2": {"$ref": "#/definitions/TestModelDuplicate2"},
        },
        "required": ["data1", "data2"],
        "definitions": {
            "TestModelDuplicate": {
                "title": "TestModelDuplicate",
                "type": "object",
                "properties": {"field1": {"title": "Field1", "type": "string"}},
                "required": ["field1"],
            },
            "TestModelDuplicate2": {
                "title": "TestModelDuplicate2",
                "type": "object",
                "properties": {"field2": {"title": "Field2", "type": "string"}},
                "required": ["field2"],
            },
        },
    }
