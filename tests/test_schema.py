from typing import List
from ninja import Schema
from ninja.schema import Field
from django.db.models import QuerySet, Manager


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


class User:
    name = "John"
    group_set = FakeManager([1, 2, 3])

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


def test_schema():
    user = User()
    schema = UserSchema.from_orm(user)
    assert schema.dict() == {
        "name": "John",
        "groups": [1, 2, 3],
        "tags": [{"id": "1", "title": "foo"}, {"id": "2", "title": "bar"}],
    }
