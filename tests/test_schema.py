from typing import List, Optional
from unittest.mock import Mock

import pytest
from django.db import models
from django.db.models import Manager, QuerySet
from django.db.models.fields.files import ImageFieldFile
from pydantic_core import ValidationError

from ninja import Schema
from ninja.orm import create_schema
from ninja.schema import DjangoGetter, Field


class FakeManager(Manager):
    def __init__(self, items):
        self._items = items

    def all(self):
        return self._items

    def __str__(self):
        return "FakeManager"


class FakeQS(QuerySet):
    def __init__(self, items):
        self._result_cache = items
        self._prefetch_related_lookups = False

    def __str__(self):
        return "FakeQS"


class Tag:
    def __init__(self, id, title):
        self.id = id
        self.title = title


# mocking some users:
class Boss:
    name = "Jane Jackson"
    title = "CEO"


class User:
    name = "John Smith"
    group_set = FakeManager([1, 2, 3])
    avatar = ImageFieldFile(None, Mock(), name=None)
    boss: Optional[Boss] = Boss()

    @property
    def tags(self):
        return FakeQS([Tag(1, "foo"), Tag(2, "bar")])

    def get_boss_title(self):
        return self.boss and self.boss.title


class TagSchema(Schema):
    id: int
    title: str


class UserSchema(Schema):
    name: str
    groups: List[int] = Field(..., alias="group_set")
    tags: List[TagSchema]
    avatar: Optional[str] = None


class UserWithBossSchema(UserSchema):
    boss: Optional[str] = Field(None, alias="boss.name")
    has_boss: bool
    boss_title: Optional[str] = Field(None, alias="get_boss_title")

    @staticmethod
    def resolve_has_boss(obj):
        return bool(obj.boss)


class UserWithInitialsSchema(UserWithBossSchema):
    initials: str

    def resolve_initials(self, obj):
        return "".join(n[:1] for n in self.name.split())


class ResolveAttrSchema(Schema):
    "The goal is to test that the resolve_xxx is not callable it should be a regular attribute"

    id: str
    resolve_attr: str


def test_schema():
    user = User()
    schema = UserSchema.from_orm(user)
    assert schema.dict() == {
        "name": "John Smith",
        "groups": [1, 2, 3],
        "tags": [{"id": 1, "title": "foo"}, {"id": 2, "title": "bar"}],
        "avatar": None,
    }


def test_schema_with_image():
    user = User()
    field = Mock()
    field.storage.url = Mock(return_value="/smile.jpg")
    user.avatar = ImageFieldFile(None, field, name="smile.jpg")
    schema = UserSchema.from_orm(user)
    assert schema.dict() == {
        "name": "John Smith",
        "groups": [1, 2, 3],
        "tags": [{"id": 1, "title": "foo"}, {"id": 2, "title": "bar"}],
        "avatar": "/smile.jpg",
    }


def test_with_boss_schema():
    user = User()
    schema = UserWithBossSchema.from_orm(user)
    assert schema.dict() == {
        "name": "John Smith",
        "boss": "Jane Jackson",
        "has_boss": True,
        "groups": [1, 2, 3],
        "tags": [{"id": 1, "title": "foo"}, {"id": 2, "title": "bar"}],
        "avatar": None,
        "boss_title": "CEO",
    }

    user_without_boss = User()
    user_without_boss.boss = None
    schema = UserWithBossSchema.from_orm(user_without_boss)
    assert schema.dict() == {
        "name": "John Smith",
        "boss": None,
        "has_boss": False,
        "boss_title": None,
        "groups": [1, 2, 3],
        "tags": [{"id": 1, "title": "foo"}, {"id": 2, "title": "bar"}],
        "avatar": None,
    }


SKIP_NON_STATIC_RESOLVES = True


@pytest.mark.skipif(SKIP_NON_STATIC_RESOLVES, reason="Lets deal with this later")
def test_with_initials_schema():
    user = User()
    schema = UserWithInitialsSchema.from_orm(user)
    assert schema.dict() == {
        "name": "John Smith",
        "initials": "JS",
        "boss": "Jane Jackson",
        "has_boss": True,
        "groups": [1, 2, 3],
        "tags": [{"id": 1, "title": "foo"}, {"id": 2, "title": "bar"}],
        "avatar": None,
        "boss_title": "CEO",
    }


def test_complex_alias_resolve():
    class Top:
        class Midddle:
            def call(self):
                return {"dict": [1, 10]}

        m = Midddle()

    class AliasSchema(Schema):
        value: int = Field(..., alias="m.call.dict.1")

    x = Top()

    assert AliasSchema.from_orm(x).dict() == {"value": 10}


def test_with_attr_that_has_resolve():
    class Obj:
        id = "1"
        resolve_attr = "2"

    assert ResolveAttrSchema.from_orm(Obj()).dict() == {"id": "1", "resolve_attr": "2"}


def test_django_getter():
    "Coverage for DjangoGetter __repr__ method"

    class Somechema(Schema):
        i: int

    dg = DjangoGetter({"i": 1}, Somechema)
    assert repr(dg) == "<DjangoGetter: {'i': 1}>"


def test_django_getter_validates_assignment():
    class ValidateAssignmentSchema(Schema):
        str_var: str

        model_config = {"validate_assignment": True}

    schema_inst = ValidateAssignmentSchema(str_var="test_value")

    # Validate we can re-assign the value, this is a test for
    # a bug where validate_assignment would cause an AttributeError
    # for __dict__ on the target schema.
    schema_inst.str_var = "reassigned_value"
    try:
        schema_inst.str_var = 5
        raise AssertionError()
    except ValidationError:
        # We expect this error, all is okay
        pass


def test_choices_default():
    class ModelWithChoices2(models.Model):
        class ThemeChoices(models.TextChoices):
            SYS = "system", "System"
            DARK = "dark", "Dark"
            LIGHT = "light", "Light"

        class ScoreChoices(models.IntegerChoices):
            GOOD = 10, "Good"
            AVERAGE = 5, "Average"
            BAD = 1, "Bad"

        theme = models.CharField(
            max_length=32, choices=ThemeChoices.choices, default=ThemeChoices.SYS
        )
        score = models.PositiveSmallIntegerField(choices=ScoreChoices.choices)

        class Meta:
            app_label = "tests"

    OrmSchema = create_schema(ModelWithChoices2)
    obj = ModelWithChoices2(score=10)
    schema = OrmSchema.from_orm(obj)
    assert schema.dict() == {
        "id": None,
        "score": 10,
        "theme": "system",
    }
