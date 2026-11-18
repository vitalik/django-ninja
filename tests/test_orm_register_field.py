"""
register_field() with field classes and relation types (#1661)
"""

import uuid
from typing import Annotated

import pytest
from django.db import models
from pydantic import BeforeValidator, ValidationError

from ninja import ModelSchema
from ninja.errors import ConfigError
from ninja.orm import create_schema, register_field
from ninja.orm import fields as orm_fields


@pytest.fixture(autouse=True)
def restore_registry():
    types = dict(orm_fields.TYPES)
    class_types = dict(orm_fields.FIELD_CLASS_TYPES)
    yield
    orm_fields.TYPES.clear()
    orm_fields.TYPES.update(types)
    orm_fields.FIELD_CLASS_TYPES.clear()
    orm_fields.FIELD_CLASS_TYPES.update(class_types)


class PrefixedID:
    "custom python value of a uuid column (like the one in #1661)"

    def __init__(self, prefix, value=None):
        self.prefix = prefix
        self.uuid = value or uuid.uuid4()

    def __str__(self):
        return f"{self.prefix}_{self.uuid.hex}"


class PrefixedIDField(models.UUIDField):
    "internal type is 'UUIDField' - so it cannot be told apart by name"

    def from_db_value(self, value, expression, connection):
        return None if value is None else PrefixedID("x", value)

    def get_prep_value(self, value):
        return value.uuid if isinstance(value, PrefixedID) else value


class SubPrefixedIDField(PrefixedIDField):
    pass


PrefixedIDStr = Annotated[str, BeforeValidator(str)]


class RfAddress(models.Model):
    id = PrefixedIDField(primary_key=True)

    class Meta:
        app_label = "tests"


class RfLocation(models.Model):
    id = PrefixedIDField(primary_key=True)
    address = models.ForeignKey(RfAddress, on_delete=models.CASCADE)
    backup = models.OneToOneField(
        RfAddress, null=True, on_delete=models.CASCADE, related_name="+"
    )
    other = SubPrefixedIDField(null=True)
    plain_uuid = models.UUIDField(null=True)

    class Meta:
        app_label = "tests"


def make_location():
    return RfLocation(
        id=PrefixedID("location"),
        address=RfAddress(id=PrefixedID("address")),
        backup=RfAddress(id=PrefixedID("backup")),
        other=PrefixedID("other"),
    )


def json_types(schema):
    "property name -> json type (ignoring the null branch of optionals)"
    result = {}
    for name, prop in schema.model_json_schema()["properties"].items():
        options = prop.get("anyOf", [prop])
        result[name] = [o for o in options if o.get("type") != "null"][0]["type"]
    return result


def test_unregistered_custom_field_maps_by_internal_type():
    # unchanged behaviour: a UUIDField subclass is a UUID for ninja
    Schema = create_schema(RfLocation, name="RfLocationUnregistered")
    with pytest.raises(ValidationError) as exc:
        Schema.from_orm(make_location())
    assert {e["loc"][0] for e in exc.value.errors()} == {
        "id",
        "address_id",
        "backup_id",
        "other",
    }


def test_register_field_class():
    register_field(PrefixedIDField, PrefixedIDStr)

    class LocationOut(ModelSchema):
        class Meta:
            model = RfLocation
            fields = "__all__"

    # the field itself, its subclass, a FK and a O2O pointing at it
    data = LocationOut.from_orm(make_location()).model_dump(by_alias=True)
    assert data["id"].startswith("location_")
    assert data["address_id"].startswith("address_")
    assert data["backup_id"].startswith("backup_")
    assert data["other"].startswith("other_")
    assert data["plain_uuid"] is None

    assert json_types(LocationOut) == {
        "id": "string",
        "address_id": "string",
        "backup_id": "string",
        "other": "string",
        "plain_uuid": "string",
    }
    # builtin UUIDFields keep their UUID type
    plain = LocationOut.model_json_schema()["properties"]["plain_uuid"]["anyOf"][0]
    assert plain == {"type": "string", "format": "uuid"}


def test_register_field_class_keeps_types_untouched():
    # TYPES keeps its meaning (internal type name -> type), some libraries read it
    before = dict(orm_fields.TYPES)
    register_field(PrefixedIDField, PrefixedIDStr)
    assert orm_fields.TYPES == before
    assert orm_fields.FIELD_CLASS_TYPES[PrefixedIDField] is PrefixedIDStr


def test_register_field_string_still_supported():
    register_field("SomeInternalType", int)
    assert orm_fields.TYPES["SomeInternalType"] is int
    assert orm_fields.FIELD_CLASS_TYPES == {}


def test_register_field_non_field_class_goes_to_types():
    # previous behaviour for anything that is not a django field class
    class NotAField:
        pass

    register_field(NotAField, int)
    assert orm_fields.TYPES[NotAField] is int
    assert NotAField not in orm_fields.FIELD_CLASS_TYPES


def test_class_registration_wins_over_internal_type():
    register_field("UUIDField", int)  # by name - would hit all UUIDFields
    register_field(PrefixedIDField, PrefixedIDStr)
    Schema = create_schema(RfLocation, name="RfLocationPriority")
    types = json_types(Schema)
    assert types["id"] == "string"  # PrefixedIDField - class registration
    assert types["other"] == "string"  # subclass of PrefixedIDField
    assert types["plain_uuid"] == "integer"  # plain UUIDField - by name


def test_most_specific_class_wins():
    register_field(PrefixedIDField, PrefixedIDStr)
    register_field(SubPrefixedIDField, int)
    Schema = create_schema(RfLocation, name="RfLocationSpecific")
    types = json_types(Schema)
    assert types["id"] == "string"
    assert types["other"] == "integer"


def test_unknown_field_error_suggests_both_forms():
    class OpaqueField(models.Field):
        def db_type(self, connection):
            return "text"

    class RfOpaque(models.Model):
        value = OpaqueField()

        class Meta:
            app_label = "tests"

    with pytest.raises(ConfigError) as exc:
        create_schema(RfOpaque)
    assert "register_field('OpaqueField', <your-python-type>)" in str(exc.value)
    assert "register_field(OpaqueField, <your-python-type>)" in str(exc.value)

    register_field(OpaqueField, str)
    assert json_types(create_schema(RfOpaque)) == {"id": "integer", "value": "string"}


def test_relation_to_unregistered_pk_falls_back_to_int():
    # unchanged behaviour: unknown related pk types are typed as int
    class OpaquePkField(models.Field):
        def db_type(self, connection):
            return "text"

    class RfOpaquePk(models.Model):
        id = OpaquePkField(primary_key=True)

        class Meta:
            app_label = "tests"

    class RfOpaqueRef(models.Model):
        target = models.ForeignKey(RfOpaquePk, on_delete=models.CASCADE)

        class Meta:
            app_label = "tests"

    Schema = create_schema(RfOpaqueRef, fields=["target"])
    assert json_types(Schema) == {"target_id": "integer"}


# ForeignKey(to_field=...) ------------------------------------------------------


class RfSlugged(models.Model):
    slug = models.SlugField(unique=True)
    code = models.IntegerField(unique=True)
    uid = models.UUIDField(unique=True, default=uuid.uuid4)

    class Meta:
        app_label = "tests"


class RfRefs(models.Model):
    by_pk = models.ForeignKey(RfSlugged, on_delete=models.CASCADE, related_name="+")
    by_slug = models.ForeignKey(
        RfSlugged, to_field="slug", on_delete=models.CASCADE, related_name="+"
    )
    by_code = models.ForeignKey(
        RfSlugged, to_field="code", on_delete=models.CASCADE, related_name="+"
    )
    by_uid = models.ForeignKey(
        RfSlugged, to_field="uid", on_delete=models.CASCADE, related_name="+"
    )
    one_by_slug = models.OneToOneField(
        RfSlugged, to_field="slug", on_delete=models.CASCADE, related_name="+"
    )
    many = models.ManyToManyField(RfSlugged, related_name="+")

    class Meta:
        app_label = "tests"


def test_foreign_key_to_field_type():
    Schema = create_schema(RfRefs)
    assert json_types(Schema) == {
        "id": "integer",
        "by_pk_id": "integer",
        "by_slug_id": "string",
        "by_code_id": "integer",
        "by_uid_id": "string",
        "one_by_slug_id": "string",
        "many": "array",
    }
    props = Schema.model_json_schema()["properties"]
    assert props["by_uid_id"]["format"] == "uuid"
    assert props["many"]["items"] == {"type": "integer"}  # m2m: related pks

    obj = RfRefs(
        id=1,
        by_pk_id=1,
        by_slug_id="hello",
        by_code_id=7,
        by_uid_id=uuid.UUID(int=1),
        one_by_slug_id="world",
    )
    NoM2M = create_schema(RfRefs, name="RfRefsNoM2M", exclude=["many"])
    data = NoM2M.from_orm(obj).model_dump(by_alias=True)
    assert data == {
        "id": 1,
        "by_pk_id": 1,
        "by_slug_id": "hello",
        "by_code_id": 7,
        "by_uid_id": uuid.UUID(int=1),
        "one_by_slug_id": "world",
    }
