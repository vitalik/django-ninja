from typing import List
from unittest.mock import Mock
from ninja import Schema
from ninja.schema import Field
from django.db.models import QuerySet, Manager
from django.db.models.fields.files import FieldFile, ImageFieldFile


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


# mocking some user:
class User:
    name = "John"
    group_set = FakeManager([1, 2, 3])
    avatar = ImageFieldFile(None, Mock(), name=None)

    @property
    def tags(self):
        return FakeQS([Tag(1, "foo"), Tag(2, "bar")])


class TagSchema(Schema):
    id: str
    title: str


class UserSchema(Schema):
    name: str
    groups: List[int] = Field(..., alias="group_set")
    tags: List[TagSchema]
    avatar: str = None


def test_schema():
    user = User()
    schema = UserSchema.from_orm(user)
    assert schema.dict() == {
        "name": "John",
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
        "name": "John",
        "groups": [1, 2, 3],
        "tags": [{"id": "1", "title": "foo"}, {"id": "2", "title": "bar"}],
        "avatar": "/smile.jpg",
    }
