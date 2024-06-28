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


def test_simple_config():
    class DummyFilterSchema(FilterSchema):
        name: Optional[str] = None

    filter_instance = DummyFilterSchema(name="foobar")
    q = filter_instance.get_filter_expression()
    assert q == Q(name="foobar")


def test_improperly_configured():
    class DummyFilterSchema(FilterSchema):
        popular: Optional[str] = Field(None, q=Q(view_count__gt=1000))

    filter_instance = DummyFilterSchema()
    with pytest.raises(ImproperlyConfigured):
        filter_instance.get_filter_expression()


def test_empty_q_when_none_ignored():
    class DummyFilterSchema(FilterSchema):
        name: Optional[str] = Field(None, q="name__icontains")
        tag: Optional[str] = Field(None, q="tag")

    filter_instance = DummyFilterSchema()
    q = filter_instance.get_filter_expression()
    assert q == Q()


@pytest.mark.parametrize("implicit_field_name", [False, True])
def test_q_expressions2(implicit_field_name):
    if implicit_field_name:
        q = "__icontains"
    else:
        q = "name__icontains"

    class DummyFilterSchema(FilterSchema):
        name: Optional[str] = Field(None, q=q)
        tag: Optional[str] = Field(None, q="tag")

    filter_instance = DummyFilterSchema(name="John", tag=None)
    q = filter_instance.get_filter_expression()
    assert q == Q(name__icontains="John")


def test_q_expressions3():
    class DummyFilterSchema(FilterSchema):
        name: Optional[str] = Field(None, q="name__icontains")
        tag: Optional[str] = Field(None, q="tag")

    filter_instance = DummyFilterSchema(name="John", tag="active")
    q = filter_instance.get_filter_expression()
    assert q == Q(name__icontains="John") & Q(tag="active")


@pytest.mark.parametrize("implicit_field_name", [False, True])
def test_q_is_a_list(implicit_field_name):
    if implicit_field_name:
        q__name = "__icontains"
    else:
        q__name = "name__icontains"

    class DummyFilterSchema(FilterSchema):
        name: Optional[str] = Field(None, q=[q__name, "user__username__icontains"])
        tag: Optional[str] = Field(None, q="tag")

    filter_instance = DummyFilterSchema(name="foo", tag="bar")
    q = filter_instance.get_filter_expression()
    assert q == (Q(name__icontains="foo") | Q(user__username__icontains="foo")) & Q(
        tag="bar"
    )


def test_field_level_expression_connector():
    class DummyFilterSchema(FilterSchema):
        name: Optional[str] = Field(
            q=["name__icontains", "user__username__icontains"],
            expression_connector="AND",
        )
        tag: Optional[str] = Field(None, q="tag")

    filter_instance = DummyFilterSchema(name="foo", tag="bar")
    q = filter_instance.get_filter_expression()
    assert q == Q(name__icontains="foo") & Q(user__username__icontains="foo") & Q(
        tag="bar"
    )


def test_class_level_expression_connector():
    class DummyFilterSchema(FilterSchema):
        tag1: Optional[str] = Field(None, q="tag1")
        tag2: Optional[str] = Field(None, q="tag2")

        class Config:
            expression_connector = "OR"

    filter_instance = DummyFilterSchema(tag1="foo", tag2="bar")
    q = filter_instance.get_filter_expression()
    assert q == Q(tag1="foo") | Q(tag2="bar")


def test_class_level_and_field_level_expression_connector():
    class DummyFilterSchema(FilterSchema):
        name: Optional[str] = Field(
            q=["name__icontains", "user__username__icontains"],
            expression_connector="AND",
        )
        tag: Optional[str] = Field(None, q="tag")

        class Config:
            expression_connector = "OR"

    filter_instance = DummyFilterSchema(name="foo", tag="bar")
    q = filter_instance.get_filter_expression()
    assert q == Q(name__icontains="foo") & Q(user__username__icontains="foo") | Q(
        tag="bar"
    )


def test_ignore_none():
    class DummyFilterSchema(FilterSchema):
        tag: Optional[str] = Field(None, q="tag", ignore_none=False)

    filter_instance = DummyFilterSchema()
    q = filter_instance.get_filter_expression()
    assert q == Q(tag=None)


def test_ignore_none_class_level():
    class DummyFilterSchema(FilterSchema):
        tag1: Optional[str] = Field(None, q="tag1")
        tag2: Optional[str] = Field(None, q="tag2")

        class Config:
            ignore_none = False

    filter_instance = DummyFilterSchema()
    q = filter_instance.get_filter_expression()
    assert q == Q(tag1=None) & Q(tag2=None)


def test_field_level_custom_expression():
    class DummyFilterSchema(FilterSchema):
        name: Optional[str] = None
        popular: Optional[bool] = None

        def filter_popular(self, value):
            return Q(downloads__gt=100) | Q(view_count__gt=1000) if value else Q()

    filter_instance = DummyFilterSchema(name="foo", popular=True)
    q = filter_instance.get_filter_expression()
    assert q == Q(name="foo") & (Q(downloads__gt=100) | Q(view_count__gt=1000))

    filter_instance = DummyFilterSchema(name="foo")
    q = filter_instance.get_filter_expression()
    assert q == Q(name="foo")

    filter_instance = DummyFilterSchema()
    q = filter_instance.get_filter_expression()
    assert q == Q()


def test_class_level_custom_expression():
    class DummyFilterSchema(FilterSchema):
        adult: Optional[bool] = Field(None, q="this_will_be_ignored")

        def custom_expression(self) -> Q:
            return Q(age__gte=18) if self.adult is True else Q()

    filter_instance = DummyFilterSchema(adult=True)
    q = filter_instance.get_filter_expression()
    assert q == Q(age__gte=18)


def test_filter_called():
    class DummyFilterSchema(FilterSchema):
        name: Optional[str] = Field(None, q="name")

    filter_instance = DummyFilterSchema(name="foobar")
    queryset = FakeQS()
    queryset = filter_instance.filter(queryset)
    assert queryset.filtered
