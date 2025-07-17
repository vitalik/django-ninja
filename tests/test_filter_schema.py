from typing import Optional

import pytest
from django.core.exceptions import ImproperlyConfigured
from django.db.models import Q, QuerySet
from pydantic import Field
from typing_extensions import Annotated

from ninja import FilterLookup, FilterSchema


class FakeQS(QuerySet):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.filtered = False

    def filter(self, *args, **kwargs):
        self.filtered = True
        return self


def test_simple_config():
    """Test basic field filtering without q parameter."""

    class DummyFilterSchema(FilterSchema):
        name: Optional[str] = None

    filter_instance = DummyFilterSchema(name="foobar")
    q = filter_instance.get_filter_expression()
    assert q == Q(name="foobar")


def test_annotated_without_filter_lookup():
    """Test Annotated field without FilterLookup instance falls back to default behavior."""

    class DummyFilterSchema(FilterSchema):
        name: Annotated[Optional[str], "some_annotation"] = None

    filter_instance = DummyFilterSchema(name="foobar")
    q = filter_instance.get_filter_expression()
    assert q == Q(name="foobar")


def test_improperly_configured_deprecated():
    """Test ImproperlyConfigured error when q is not a string or list of strings (deprecated Field approach)."""

    class DummyFilterSchema(FilterSchema):
        popular: Optional[str] = Field(None, q=Q(view_count__gt=1000))

    filter_instance = DummyFilterSchema()
    with pytest.raises(ImproperlyConfigured):
        filter_instance.get_filter_expression()


def test_improperly_configured_annotated():
    """Test ImproperlyConfigured error when q is not a string or list of strings (FilterLookup annotation)."""

    class DummyFilterSchema(FilterSchema):
        popular: Annotated[Optional[str], FilterLookup(Q(view_count__gt=1000))] = None

    filter_instance = DummyFilterSchema()
    with pytest.raises(ImproperlyConfigured):
        filter_instance.get_filter_expression()


def test_empty_q_when_none_ignored_deprecated():
    """Test empty Q expression when None values are ignored (deprecated Field approach)."""

    class DummyFilterSchema(FilterSchema):
        name: Optional[str] = Field(None, q="name__icontains")
        tag: Optional[str] = Field(None, q="tag")

    filter_instance = DummyFilterSchema()
    q = filter_instance.get_filter_expression()
    assert q == Q()


def test_empty_q_when_none_ignored_annotated():
    """Test empty Q expression when None values are ignored (FilterLookup annotation)."""

    class DummyFilterSchema(FilterSchema):
        name: Annotated[Optional[str], FilterLookup("name__icontains")] = None
        tag: Annotated[Optional[str], FilterLookup("tag")] = None

    filter_instance = DummyFilterSchema()
    q = filter_instance.get_filter_expression()
    assert q == Q()


@pytest.mark.parametrize("implicit_field_name", [False, True])
def test_q_expressions2_deprecated(implicit_field_name):
    """Test implicit vs explicit field names in q expressions (deprecated Field approach)."""
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


@pytest.mark.parametrize("implicit_field_name", [False, True])
def test_q_expressions2_annotated(implicit_field_name):
    """Test implicit vs explicit field names in q expressions (FilterLookup annotation)."""
    if implicit_field_name:
        q = "__icontains"
    else:
        q = "name__icontains"

    class DummyFilterSchema(FilterSchema):
        name: Annotated[Optional[str], FilterLookup(q)] = None
        tag: Annotated[Optional[str], FilterLookup("tag")] = None

    filter_instance = DummyFilterSchema(name="John", tag=None)
    q = filter_instance.get_filter_expression()
    assert q == Q(name__icontains="John")


def test_q_expressions3_deprecated():
    """Test multiple fields with different q expressions (deprecated Field approach)."""

    class DummyFilterSchema(FilterSchema):
        name: Optional[str] = Field(None, q="name__icontains")
        tag: Optional[str] = Field(None, q="tag")

    filter_instance = DummyFilterSchema(name="John", tag="active")
    q = filter_instance.get_filter_expression()
    assert q == Q(name__icontains="John") & Q(tag="active")


def test_q_expressions3_annotated():
    """Test multiple fields with different q expressions (FilterLookup annotation)."""

    class DummyFilterSchema(FilterSchema):
        name: Annotated[Optional[str], FilterLookup("name__icontains")] = None
        tag: Annotated[Optional[str], FilterLookup("tag")] = None

    filter_instance = DummyFilterSchema(name="John", tag="active")
    q = filter_instance.get_filter_expression()
    assert q == Q(name__icontains="John") & Q(tag="active")


@pytest.mark.parametrize("implicit_field_name", [False, True])
def test_q_is_a_list_deprecated(implicit_field_name):
    """Test q as list of lookups with OR connector (deprecated Field approach)."""
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


@pytest.mark.parametrize("implicit_field_name", [False, True])
def test_q_is_a_list_annotated(implicit_field_name):
    """Test q as list of lookups with OR connector (FilterLookup annotation)."""
    if implicit_field_name:
        q__name = "__icontains"
    else:
        q__name = "name__icontains"

    class DummyFilterSchema(FilterSchema):
        name: Annotated[
            Optional[str], FilterLookup([q__name, "user__username__icontains"])
        ] = None
        tag: Annotated[Optional[str], FilterLookup("tag")] = None

    filter_instance = DummyFilterSchema(name="foo", tag="bar")
    q = filter_instance.get_filter_expression()
    assert q == (Q(name__icontains="foo") | Q(user__username__icontains="foo")) & Q(
        tag="bar"
    )


def test_field_level_expression_connector_deprecated():
    """Test field-level expression connector (deprecated Field approach)."""

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


def test_field_level_expression_connector_annotated():
    """Test field-level expression connector (FilterLookup annotation)."""

    class DummyFilterSchema(FilterSchema):
        name: Annotated[
            Optional[str],
            FilterLookup(
                ["name__icontains", "user__username__icontains"],
                expression_connector="AND",
            ),
        ] = None
        tag: Annotated[Optional[str], FilterLookup("tag")] = None

    filter_instance = DummyFilterSchema(name="foo", tag="bar")
    q = filter_instance.get_filter_expression()
    assert q == Q(name__icontains="foo") & Q(user__username__icontains="foo") & Q(
        tag="bar"
    )


def test_class_level_expression_connector_deprecated():
    """Test class-level expression connector (deprecated Field approach)."""

    class DummyFilterSchema(FilterSchema):
        tag1: Optional[str] = Field(None, q="tag1")
        tag2: Optional[str] = Field(None, q="tag2")

        class Config:
            expression_connector = "OR"

    filter_instance = DummyFilterSchema(tag1="foo", tag2="bar")
    q = filter_instance.get_filter_expression()
    assert q == Q(tag1="foo") | Q(tag2="bar")


def test_class_level_expression_connector_annotated():
    """Test class-level expression connector (FilterLookup annotation)."""

    class DummyFilterSchema(FilterSchema):
        tag1: Annotated[Optional[str], FilterLookup("tag1")] = None
        tag2: Annotated[Optional[str], FilterLookup("tag2")] = None

        class Config:
            expression_connector = "OR"

    filter_instance = DummyFilterSchema(tag1="foo", tag2="bar")
    q = filter_instance.get_filter_expression()
    assert q == Q(tag1="foo") | Q(tag2="bar")


def test_class_level_and_field_level_expression_connector_deprecated():
    """Test both class-level and field-level expression connectors (deprecated Field approach)."""

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


def test_class_level_and_field_level_expression_connector_annotated():
    """Test both class-level and field-level expression connectors (FilterLookup annotation)."""

    class DummyFilterSchema(FilterSchema):
        name: Annotated[
            Optional[str],
            FilterLookup(
                ["name__icontains", "user__username__icontains"],
                expression_connector="AND",
            ),
        ] = None
        tag: Annotated[Optional[str], FilterLookup("tag")] = None

        class Config:
            expression_connector = "OR"

    filter_instance = DummyFilterSchema(name="foo", tag="bar")
    q = filter_instance.get_filter_expression()
    assert q == Q(name__icontains="foo") & Q(user__username__icontains="foo") | Q(
        tag="bar"
    )


def test_ignore_none_deprecated():
    """Test field-level ignore_none setting (deprecated Field approach)."""

    class DummyFilterSchema(FilterSchema):
        tag: Optional[str] = Field(None, q="tag", ignore_none=False)

    filter_instance = DummyFilterSchema()
    q = filter_instance.get_filter_expression()
    assert q == Q(tag=None)


def test_ignore_none_annotated():
    """Test field-level ignore_none setting (FilterLookup annotation)."""

    class DummyFilterSchema(FilterSchema):
        tag: Annotated[Optional[str], FilterLookup("tag", ignore_none=False)] = None

    filter_instance = DummyFilterSchema()
    q = filter_instance.get_filter_expression()
    assert q == Q(tag=None)


def test_ignore_none_class_level_deprecated():
    """Test class-level ignore_none setting (deprecated Field approach)."""

    class DummyFilterSchema(FilterSchema):
        tag1: Optional[str] = Field(None, q="tag1")
        tag2: Optional[str] = Field(None, q="tag2")

        class Config:
            ignore_none = False

    filter_instance = DummyFilterSchema()
    q = filter_instance.get_filter_expression()
    assert q == Q(tag1=None) & Q(tag2=None)


def test_ignore_none_class_level_annotated():
    """Test class-level ignore_none setting (FilterLookup annotation)."""

    class DummyFilterSchema(FilterSchema):
        tag1: Annotated[Optional[str], FilterLookup("tag1")] = None
        tag2: Annotated[Optional[str], FilterLookup("tag2")] = None

        class Config:
            ignore_none = False

    filter_instance = DummyFilterSchema()
    q = filter_instance.get_filter_expression()
    assert q == Q(tag1=None) & Q(tag2=None)


def test_field_level_custom_expression():
    """Test custom filter_* methods override field configuration."""

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
    """Test custom_expression method overrides all field configuration."""

    class DummyFilterSchema(FilterSchema):
        adult: Annotated[Optional[bool], FilterLookup("this_will_be_ignored")] = None

        def custom_expression(self) -> Q:
            return Q(age__gte=18) if self.adult is True else Q()

    filter_instance = DummyFilterSchema(adult=True)
    q = filter_instance.get_filter_expression()
    assert q == Q(age__gte=18)


def test_filter_called():
    """Test filter() method applies expression to queryset (FilterLookup annotation)."""

    class DummyFilterSchema(FilterSchema):
        name: Annotated[Optional[str], FilterLookup("name")] = None

    filter_instance = DummyFilterSchema(name="foobar")
    queryset = FakeQS()
    queryset = filter_instance.filter(queryset)
    assert queryset.filtered


def test_multiple_filter_lookup_instances_error():
    """Test that multiple FilterLookup instances in a single annotation raises ImproperlyConfigured."""

    class DummyFilterSchema(FilterSchema):
        name: Annotated[
            Optional[str], FilterLookup("name__icontains"), FilterLookup("name__exact")
        ] = None

    filter_instance = DummyFilterSchema(name="test")
    with pytest.raises(ImproperlyConfigured):
        filter_instance.get_filter_expression()
