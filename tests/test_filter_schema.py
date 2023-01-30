from typing import Optional

import pytest
from django.core.exceptions import ImproperlyConfigured
from django.db.models import Q, QuerySet
from pydantic import Field

from ninja import FilterSchema


class FakeQS(QuerySet):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.filtered = False

    def filter(self, *args, **kwargs):
        self.filtered = True
        return self


def test_absent_q_expression():
    class DummyFilterSchema(FilterSchema):
        name: Optional[str]

    filter_instance = DummyFilterSchema()
    with pytest.raises(ImproperlyConfigured):
        filter_instance.get_filter_expression()


def test_q_expressions1():
    class DummyFilterSchema(FilterSchema):
        name: Optional[str] = Field(q="name__icontains")
        tag: Optional[str] = Field(q="tag")

    filter_instance = DummyFilterSchema()
    q = filter_instance.get_filter_expression()
    assert q == Q()


def test_q_expressions2():
    class DummyFilterSchema(FilterSchema):
        name: Optional[str] = Field(q="name__icontains")
        tag: Optional[str] = Field(q="tag")

    filter_instance = DummyFilterSchema(name="John", tag=None)
    q = filter_instance.get_filter_expression()
    assert q == Q(name__icontains="John")


def test_q_expressions3():
    class DummyFilterSchema(FilterSchema):
        name: Optional[str] = Field(q="name__icontains")
        tag: Optional[str] = Field(q="tag")

    filter_instance = DummyFilterSchema(name="John", tag="active")
    q = filter_instance.get_filter_expression()
    assert q == Q(name__icontains="John") & Q(tag="active")


def test_ignore_none():
    class DummyFilterSchema(FilterSchema):
        tag: str | None = Field(q="tag", ignore_none=False)

    filter_instance = DummyFilterSchema()
    q = filter_instance.get_filter_expression()
    assert q == Q(tag=None)


def test_ignore_none_class_level():
    class DummyFilterSchema(FilterSchema):
        tag1: Optional[str] = Field(q="tag1")
        tag2: Optional[str] = Field(q="tag2")

        class Config:
            ignore_none = False

    filter_instance = DummyFilterSchema()
    q = filter_instance.get_filter_expression()
    assert q == Q(tag1=None) & Q(tag2=None)


def test_expression_connector():
    class DummyFilterSchema(FilterSchema):
        tag1: Optional[str] = Field(q="tag1")
        tag2: Optional[str] = Field(q="tag2")

        class Config:
            expression_connector = "OR"

    filter_instance = DummyFilterSchema(tag1="foo", tag2="bar")
    q = filter_instance.get_filter_expression()
    assert q == Q(tag1="foo") | Q(tag2="bar")


def test_custom_expression():
    class DummyFilterSchema(FilterSchema):
        adult: Optional[bool] = Field(q="this_will_be_ignored")

        def custom_expression(self) -> Q:
            return Q(age__gte=18) if self.adult is True else Q()

    filter_instance = DummyFilterSchema(adult=True)
    q = filter_instance.get_filter_expression()
    assert q == Q(age__gte=18)


def test_filter_called():
    class DummyFilterSchema(FilterSchema):
        name: Optional[str] = Field(q="name")

    filter_instance = DummyFilterSchema(name="foobar")
    queryset = FakeQS()
    queryset = filter_instance.filter(queryset)
    assert queryset.filtered
