# Filtering

For query parameters that map onto a database lookup, encapsulate the filtering logic
in a `FilterSchema`. It is a regular [`Schema`](schemas.md), so you get all of
Pydantic's parsing and validation, plus a `.filter()` helper that turns the schema's
fields into a Django ORM `Q` expression.

## Basic usage

Define a subclass of `FilterSchema` and use it together with `Query`, exactly like a
[query parameter schema](query-params.md#grouping-parameters-into-a-schema):

```python hl_lines="7-10 14 16"
from ninja import FilterSchema, NinjaAPI, Query
from datetime import datetime

api = NinjaAPI()


class BookFilterSchema(FilterSchema):
    name: str | None = None
    author: str | None = None
    created_after: datetime | None = None


@api.get("/books")
def list_books(request, filters: Query[BookFilterSchema]):
    books = Book.objects.all()
    books = filters.filter(books)
    return books
```

Calling `.filter()` on the schema instance applies the filters to a queryset and
returns the filtered queryset. Under the hood, each field is turned into a `Q`
expression, and all of them are combined and passed to `queryset.filter(...)`.

By default:

- a `None` value is ignored — the field is not filtered on at all;
- every other field is turned into `Q(field_name=value)`;
- all fields' expressions are combined with `AND`.

So with `?name=hobbit&created_after=2020-01-01`, the example above filters for
`Q(name="hobbit") & Q(created_after=...)`, while a request with just `?name=hobbit`
skips the `created_after` clause entirely.

If you need the `Q` expression itself rather than an already-filtered queryset — for
example to combine it with filtering the API doesn't expose to the user — call
`get_filter_expression()` instead:

```python hl_lines="7 10"
from django.db.models import Q


@api.get("/books")
def list_books(request, filters: Query[BookFilterSchema]):
    # Never serve inactive books, or books from an inactive publisher
    q = Q(is_active=True) & Q(publisher__is_active=True)

    # ... and layer the user's filters on top
    q &= filters.get_filter_expression()
    return Book.objects.filter(q)
```

## Custom lookups with `FilterLookup`

By default, a field's name is used as the lookup: `name: str | None = None` becomes
`Q(name=value)`. Annotate a field with `FilterLookup` when you need a different
lookup, such as `icontains` for a case-insensitive search:

```python hl_lines="1 2 6"
from typing import Annotated
from ninja import FilterLookup, FilterSchema


class BookFilterSchema(FilterSchema):
    name: Annotated[str | None, FilterLookup("name__icontains")] = None
```

Pass a list of lookups to search across several fields at once:

```python hl_lines="2-7"
class BookFilterSchema(FilterSchema):
    search: Annotated[
        str | None,
        FilterLookup(
            ["name__icontains", "author__name__icontains", "publisher__name__icontains"]
        ),
    ] = None
```

Multiple lookups for the same field are combined with `OR` by default, so
`?search=foobar` matches books with "foobar" in their name, author's name, or
publisher's name.

You can also skip the field name and let `FilterLookup` fill it in, which is handy for
a reusable, generic lookup:

```python hl_lines="1 5"
IContainsField = Annotated[str | None, FilterLookup("__icontains")]


class BookFilterSchema(FilterSchema):
    name: IContainsField = None
```

A lookup string starting with `__` has the field's own name prepended to it, so
`"__icontains"` on the `name` field becomes `"name__icontains"`.

!!! note "Deprecated: `Field(q=...)`"
    Older code may specify the lookup as a keyword argument to Pydantic's `Field`
    instead:

    ```python
    from ninja import FilterSchema
    from pydantic import Field

    class BookFilterSchema(FilterSchema):
        name: str | None = Field(None, q="name__icontains")
    ```

    This still works, but raises a `DeprecationWarning` — `FilterLookup` is
    type-safe and IDE-friendly, `Field(q=...)` is neither. Prefer `FilterLookup` for
    new code.

## Combining expressions

Two independent settings control how expressions are combined, and each can be set
at the field level (`FilterLookup(..., expression_connector=...)`) or for the whole
schema (`model_config = FilterConfigDict(expression_connector=...)`):

- **field-level connector** — how a single field's own multiple lookups are joined
  together. Defaults to `"OR"`.
- **class-level connector** — how the (already-resolved) expressions of *different*
  fields are joined together. Defaults to `"AND"`.

```python hl_lines="7 11"
from ninja import FilterConfigDict, FilterLookup, FilterSchema


class BookFilterSchema(FilterSchema):
    active: Annotated[
        bool | None,
        FilterLookup(["is_active", "publisher__is_active"], expression_connector="AND"),
    ] = None
    name: Annotated[str | None, FilterLookup("name__icontains")] = None

    model_config = FilterConfigDict(expression_connector="OR")
```

Here, `?name=harry&active=true` matches books that are active *and* published by an
active publisher, *or* that have "harry" in their name — the `active` field's two
lookups are AND-ed together, then the two fields' results are OR-ed together.

The accepted values are `"AND"`, `"OR"` and `"XOR"`. `"XOR"` is only
[supported by Django from version 4.1](https://docs.djangoproject.com/en/stable/ref/models/querysets/#xor).

## Filtering by `None`

By default, a field left out of the request (so it's `None`) is skipped entirely —
it does not turn into `Q(field=None)`. Set `ignore_none=False`, on a field or for the
whole schema, to filter on `None` explicitly whenever no other value is supplied:

```python hl_lines="3"
class BookFilterSchema(FilterSchema):
    name: Annotated[str | None, FilterLookup("name__icontains")] = None
    tag: Annotated[str | None, FilterLookup("tag", ignore_none=False)] = None
```

```python hl_lines="5"
class BookFilterSchema(FilterSchema):
    name: str | None = None
    tag: str | None = None

    model_config = FilterConfigDict(ignore_none=False)
```

!!! warning
    The class-level `ignore_none` only overrides field-level settings when it is set
    to `False`; the class-level default of `True` never overrides a field that
    explicitly sets `ignore_none=False`.

## Custom filtering methods

For logic that a lookup string can't express, define a `filter_<field_name>` method.
It receives the field's value and must return a `Q` expression; it takes precedence
over any `FilterLookup` on that field:

```python hl_lines="9-10"
from django.db.models import Q
from ninja import FilterSchema


class BookFilterSchema(FilterSchema):
    tag: str | None = None
    popular: bool | None = None

    def filter_popular(self, value: bool) -> Q:
        return (Q(view_count__gt=1000) | Q(download_count__gt=100)) if value else Q()
```

For filtering that spans several fields at once — or that needs to fall back to the
default behavior for some fields but not others — override `custom_expression()`
instead. It takes precedence over everything else, including `filter_<field_name>`
methods:

```python hl_lines="9-19"
from django.db.models import Q
from ninja import FilterSchema


class BookFilterSchema(FilterSchema):
    name: str | None = None
    popular: bool | None = None

    def custom_expression(self) -> Q:
        q = Q()
        if self.name:
            q &= Q(name__icontains=self.name)
        if self.popular:
            q &= (
                Q(view_count__gt=1000)
                | Q(download_count__gt=100)
                | Q(tag="popular")
            )
        return q
```

## Combining with pagination

`FilterSchema` returns a plain queryset, so it composes with
[pagination](pagination.md) the same way any other queryset-returning view does —
apply the filters first, then let pagination handle the rest:

```python hl_lines="11 13"
from ninja import Schema
from ninja.pagination import paginate


class BookSchema(Schema):
    id: int
    name: str


@api.get("/books", response=list[BookSchema])
@paginate
def list_books(request, filters: Query[BookFilterSchema]):
    return filters.filter(Book.objects.all())
```
