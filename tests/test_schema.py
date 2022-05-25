from typing import List, Optional
from unittest.mock import Mock

from django.db.models import Manager, QuerySet
from django.db.models.fields.files import ImageFieldFile

from ninja import Schema
from ninja.schema import Field


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
    id: str
    title: str


class UserSchema(Schema):
    name: str
    groups: List[int] = Field(..., alias="group_set")
    tags: List[TagSchema]
    avatar: str = None


class UserWithBossSchema(UserSchema):
    boss: Optional[str] = Field(None, alias="boss.name")
    has_boss: bool
    boss_title: str = Field(None, alias="get_boss_title")

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
        "tags": [{"id": "1", "title": "foo"}, {"id": "2", "title": "bar"}],
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
        "tags": [{"id": "1", "title": "foo"}, {"id": "2", "title": "bar"}],
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
        "tags": [{"id": "1", "title": "foo"}, {"id": "2", "title": "bar"}],
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
        "tags": [{"id": "1", "title": "foo"}, {"id": "2", "title": "bar"}],
        "avatar": None,
    }


def test_with_initials_schema():
    user = User()
    schema = UserWithInitialsSchema.from_orm(user)
    assert schema.dict() == {
        "name": "John Smith",
        "initials": "JS",
        "boss": "Jane Jackson",
        "has_boss": True,
        "groups": [1, 2, 3],
        "tags": [{"id": "1", "title": "foo"}, {"id": "2", "title": "bar"}],
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
        id = 1
        resolve_attr = 2

    assert ResolveAttrSchema.from_orm(Obj()).dict() == {"id": "1", "resolve_attr": "2"}
