"""
How Schema reads its input: dicts go to pydantic as they are, any other object
has its fields read into a dict first.
"""

import warnings
from typing import List, Optional

import pytest
from pydantic import (
    AliasChoices,
    AliasPath,
    ConfigDict,
    field_validator,
    model_validator,
)
from pydantic.alias_generators import to_camel
from pydantic_core import ValidationError

from ninja import Schema
from ninja.errors import ConfigError
from ninja.schema import Field


class Obj:
    def __init__(self, **kwargs):
        self.__dict__.update(kwargs)


def test_before_validator_receives_dict():
    seen = []

    class Item(Schema):
        a: int

        @model_validator(mode="before")
        @classmethod
        def check(cls, data):
            seen.append(data)
            return data

    Item.model_validate({"a": 1})
    Item.model_validate(Obj(a=2, other="ignored"))
    assert seen == [{"a": 1}, {"a": 2}]


def test_before_validator_can_change_data():
    class Item(Schema):
        a: int

        @model_validator(mode="before")
        @classmethod
        def increment(cls, data):
            return {**data, "a": data["a"] + 1}

    assert Item.model_validate({"a": 1}).a == 2
    assert Item.model_validate(Obj(a=1)).a == 2


def test_extra_forbid_validates_once():
    calls = []

    class Leaf(Schema):
        model_config = ConfigDict(extra="forbid")
        v: int

        @field_validator("v")
        @classmethod
        def count(cls, v):
            calls.append(v)
            return v

    class Middle(Schema):
        model_config = ConfigDict(extra="forbid")
        leaf: Leaf

    class Top(Schema):
        model_config = ConfigDict(extra="forbid")
        middle: Middle

    Top.model_validate({"middle": {"leaf": {"v": 1}}})
    assert calls == [1]

    with pytest.raises(ValidationError) as e:
        Top.model_validate({"middle": {"leaf": {"v": 1, "x": 2}}})
    assert e.value.errors()[0]["type"] == "extra_forbidden"
    assert e.value.errors()[0]["loc"] == ("middle", "leaf", "x")


def test_extra_forbid_with_resolver():
    class Item(Schema):
        model_config = ConfigDict(extra="forbid")
        a: int

        @staticmethod
        def resolve_a(obj):
            return 5

    assert Item.model_validate({}).a == 5

    with pytest.raises(ValidationError) as e:
        Item.model_validate({"x": 1})
    assert e.value.errors()[0]["type"] == "extra_forbidden"


def test_extra_allow_keeps_dict_extras():
    class Item(Schema):
        model_config = ConfigDict(extra="allow")
        a: int

    assert Item.model_validate({"a": 1, "x": 2}).model_dump() == {"a": 1, "x": 2}
    # ... also when a value has to be converted
    data = {"a": lambda: 1, "x": 2}
    assert Item.model_validate(data).model_dump() == {"a": 1, "x": 2}
    assert callable(data["a"]), "the input dict is not modified"


@pytest.mark.parametrize("value", ["oops", 123, [1, 2], None])
def test_non_object_input_is_rejected(value):
    class Item(Schema):
        a: int = 1

    class Parent(Schema):
        item: Item

    for schema, data in ((Item, value), (Parent, {"item": value})):
        with pytest.raises(ValidationError) as e:
            schema.model_validate(data)
        assert e.value.errors()[0]["type"] == "model_attributes_type"


def test_dict_subclass_input():
    class MyDict(dict):
        pass

    class Item(Schema):
        a: int
        b: int = 2

    assert Item.model_validate(MyDict(a=1, x=5)).model_dump() == {"a": 1, "b": 2}


def test_mapping_like_object_input():
    "An object without the attribute is tried as obj[key]"

    class Row:
        def __getitem__(self, key):
            return {"a": 1}[key]

    class Item(Schema):
        a: int
        b: int = 2

    assert Item.model_validate(Row()).model_dump() == {"a": 1, "b": 2}


def test_alias_and_name_lookups():
    class Camel(Schema):
        model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)
        first_name: str
        last_name: str = "x"

    assert Camel.model_validate(Obj(first_name="a")).first_name == "a"
    assert Camel.model_validate(Obj(firstName="b", first_name="a")).first_name == "b"
    assert Camel.model_validate({"firstName": "c"}).first_name == "c"

    class AliasOnly(Schema):
        a: int = Field(alias="aa")

    assert AliasOnly.model_validate(Obj(aa=1)).a == 1
    with pytest.raises(ValidationError):
        AliasOnly.model_validate(Obj(a=1))

    class SameAlias(Schema):
        model_config = ConfigDict(populate_by_name=True)
        a: int = Field(alias="a")

    assert SameAlias.model_validate(Obj(a=1)).a == 1


def test_alias_that_is_not_a_template_variable():
    "Aliases that django's template Variable would reject or read as constants"

    class Item(Schema):
        model_config = ConfigDict(populate_by_name=True)
        policy: Optional[str] = Field(None, alias="CloudFront-Policy")
        private: Optional[str] = Field(None, alias="_id")
        number: Optional[int] = Field(None, alias="0")
        decimal: Optional[float] = Field(None, alias="1.5")

    item = Item.model_validate(Obj(policy="p", private="x", number=1, decimal=2.5))
    assert item.model_dump() == {
        "policy": "p",
        "private": "x",
        "number": 1,
        "decimal": 2.5,
    }
    assert Item.model_validate(Obj()).model_dump() == {
        "policy": None,
        "private": None,
        "number": None,
        "decimal": None,
    }


def test_alias_path_from_object():
    class Item(Schema):
        boss: str = Field(validation_alias=AliasPath("boss", "first_name"))
        title: str = Field("none", validation_alias=AliasPath("boss", "job", "title"))
        tag: str = Field("none", validation_alias=AliasPath("tags", 0))
        meta: int = Field(0, validation_alias=AliasPath("meta", "x"))
        initial: str = Field("none", validation_alias=AliasPath("name", 0))

    item = Item.model_validate(
        Obj(
            boss=Obj(first_name="Bob", job=Obj(title="CEO")),
            tags=["a", "b"],
            meta={"x": 1},
            name="string is not indexed",
        )
    )
    assert item.model_dump() == {
        "boss": "Bob",
        "title": "CEO",
        "tag": "a",
        "meta": 1,
        "initial": "none",
    }

    # steps that are missing fall back to the default
    item = Item.model_validate(Obj(boss=Obj(first_name="Bob"), tags=[], meta={}))
    assert item.model_dump() == {
        "boss": "Bob",
        "title": "none",
        "tag": "none",
        "meta": 0,
        "initial": "none",
    }

    with pytest.raises(ValidationError) as e:
        Item.model_validate(Obj())
    assert e.value.errors()[0]["type"] == "missing"


def test_alias_choices_from_object():
    class Item(Schema):
        name: str = Field(
            validation_alias=AliasChoices("nick", AliasPath("boss", "first_name"))
        )

    assert Item.model_validate(Obj(boss=Obj(first_name="Bob"))).name == "Bob"
    assert Item.model_validate(Obj(nick="B", boss=None)).name == "B"
    assert Item.model_validate({"boss": {"first_name": "Bob"}}).name == "Bob"


def test_alias_path_from_dict_with_values_to_convert():
    class Item(Schema):
        boss: str = Field(validation_alias=AliasPath("boss", "first_name"))
        other: str = Field("none", validation_alias=AliasPath("other", "x"))
        tags: List[str] = []

    item = Item.model_validate({
        "boss": lambda: {"first_name": "Bob"},
        "other": {},
        "tags": lambda: ["a"],
    })
    assert item.model_dump() == {"boss": "Bob", "other": "none", "tags": ["a"]}


def test_alias_path_conflict():
    class Boss(Schema):
        first_name: str

    class Item(Schema):
        boss: Boss
        boss_name: str = Field(validation_alias=AliasPath("boss", "first_name"))

    with pytest.raises(ConfigError, match="can't be combined"):
        Item.model_validate(Obj(boss=Obj(first_name="Bob")))

    # a dict is not affected, and the dotted alias works for objects
    item = Item.model_validate({"boss": {"first_name": "Bob"}})
    assert item.boss_name == "Bob"

    class ItemDotted(Schema):
        boss: Boss
        boss_name: str = Field(alias="boss.first_name")

    item = ItemDotted.model_validate(Obj(boss=Obj(first_name="Bob")))
    assert item.model_dump() == {"boss": {"first_name": "Bob"}, "boss_name": "Bob"}


def test_failing_attribute():
    class Source:
        ok = 1

        @property
        def broken(self):
            raise ValueError("boom")

        @property
        def missing(self):
            raise AttributeError("looks like a missing attribute")

    class Item(Schema):
        ok: int
        broken: int = 0
        missing: int = 7
        nested_missing: int = 8

    class OkOnly(Schema):
        ok: int
        missing: int = 7
        dotted: int = Field(8, alias="missing.real")

    assert OkOnly.model_validate(Source()).model_dump() == {
        "ok": 1,
        "missing": 7,
        "dotted": 8,
    }

    with pytest.raises(ValidationError) as e:
        Item.model_validate(Source())
    errors = e.value.errors()
    assert len(errors) == 1
    assert errors[0]["type"] == "get_attribute_error"
    assert errors[0]["loc"] == ("broken",)
    assert "ValueError: boom" in errors[0]["msg"]


def test_failing_resolver():
    class Item(Schema):
        a: int

        @staticmethod
        def resolve_a(obj):
            raise RuntimeError("boom")

    class Parent(Schema):
        item: Item

    with pytest.raises(ValidationError) as e:
        Parent.model_validate({"item": {"a": 1}})
    errors = e.value.errors()
    assert errors[0]["type"] == "get_attribute_error"
    assert errors[0]["loc"] == ("item", "a")


def test_django_getter_is_deprecated():
    with pytest.warns(DeprecationWarning, match="DjangoGetter is deprecated"):
        from ninja.schema import DjangoGetter

    class Item(Schema):
        a: int

        @model_validator(mode="before")
        @classmethod
        def unwrap(cls, values):
            # code written for the wrapper keeps working
            if isinstance(values, DjangoGetter):
                values = values._obj  # pragma: no cover
            return values

    assert Item.model_validate({"a": 1}).a == 1

    from ninja import schema

    with pytest.raises(AttributeError):
        getattr(schema, "NoSuchName")  # noqa: B009

    with warnings.catch_warnings():
        warnings.simplefilter("error")
        from ninja.schema import Schema as SchemaAgain  # no warning

        assert SchemaAgain is Schema
