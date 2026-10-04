# Pagination

Pagination splits a large list response into pages, so an operation returns a
manageable slice of a queryset instead of the whole thing at once. Django
Ninja adds pagination to an operation with a single decorator, which injects
the paginator's own query parameters (`limit`/`offset`, `page`, `cursor`, ...)
and wraps the response in a schema that carries the page's items alongside
paging metadata.

## Basic usage

Apply the `paginate` decorator to any operation whose `response` is a list:

```python hl_lines="3 14"
from django.contrib.auth.models import User
from ninja import NinjaAPI, Schema
from ninja.pagination import paginate

api = NinjaAPI()


class UserSchema(Schema):
    id: int
    username: str


@api.get("/users", response=list[UserSchema])
@paginate
def list_users(request):
    return User.objects.all()
```

That's it - `list_users` can now be queried with `limit` and `offset`:

```
GET /api/users?limit=10&offset=0
```

and the response is wrapped with paging metadata:

```json
{
  "items": [{"id": 1, "username": "alice"}, ...],
  "count": 57
}
```

Without `@paginate`, the view would need to return the whole queryset (and
the response would need to match it exactly). With it, only the current page
is evaluated and serialized, and the `response` annotation still describes
`UserSchema` - Django Ninja generates the wrapping page schema for you.

If `limit` is omitted, it defaults to 100 (`NINJA_PAGINATION_PER_PAGE` in
your settings). The pagination class used when you just write `@paginate` -
here and everywhere else in the app - is controlled by `NINJA_PAGINATION_CLASS`,
which defaults to `LimitOffsetPagination`. See [Settings](settings.md) for the
full list of settings.

## Built-in pagination classes

Pass a specific class to `@paginate` to use it for one operation, regardless
of the `NINJA_PAGINATION_CLASS` default:

```python
@paginate(PageNumberPagination)
```

### LimitOffsetPagination (default)

```python hl_lines="1 4"
from ninja.pagination import LimitOffsetPagination, paginate

@api.get("/users", response=list[UserSchema])
@paginate(LimitOffsetPagination)
def list_users(request):
    return User.objects.all()
```

```
GET /api/users?limit=10&offset=0
```

Input parameters:

- `limit` - number of items to return. Defaults to 100
  (`NINJA_PAGINATION_PER_PAGE`).
- `offset` - number of items to skip. Defaults to `0`.

`limit` is additionally capped by the `max_limit` constructor argument, which
defaults to `NINJA_PAGINATION_MAX_LIMIT` (unbounded, unless you set it):

```python hl_lines="1"
@paginate(LimitOffsetPagination, max_limit=500)
def list_users(request):
    ...
```

### PageNumberPagination

```python hl_lines="1 4"
from ninja.pagination import PageNumberPagination, paginate

@api.get("/users", response=list[UserSchema])
@paginate(PageNumberPagination)
def list_users(request):
    return User.objects.all()
```

```
GET /api/users?page=2
```

Input parameters:

- `page` - page number, starting at `1`. Defaults to `1`.
- `page_size` - overrides the page size for this request only.

The page size otherwise defaults to the `page_size` constructor argument
(itself defaulting to `NINJA_PAGINATION_PER_PAGE`), and a client-supplied
`page_size` is capped at `max_page_size` (defaults to
`NINJA_MAX_PER_PAGE_SIZE`, 100):

```python hl_lines="2"
@api.get("/users", response=list[UserSchema])
@paginate(PageNumberPagination, page_size=50)
def list_users(request):
    return User.objects.all()
```

```
GET /api/users?page=2&page_size=20
```

### CursorPagination

Cursor pagination gives stable pages for a dataset that changes between
requests (items added or removed don't shift other pages around, unlike
`limit`/`offset`). Each response carries opaque, base64-encoded `next` and
`previous` cursors instead of a page number:

```python hl_lines="1 4"
from ninja.pagination import CursorPagination, paginate

@api.get("/users", response=list[UserSchema])
@paginate(CursorPagination)
def list_users(request):
    return User.objects.all()
```

```
GET /api/users?cursor=cD0yMDI0LTAxLTAx
```

```json
{
  "next": "http://api.example.com/users?cursor=cD0yMDI0LTAxLTAy",
  "previous": null,
  "results": [
    {"id": 1, "username": "alice"},
    {"id": 2, "username": "bob"}
  ]
}
```

Input parameters:

- `cursor` - opaque position token. Omit it to start from the beginning.
- `page_size` - overrides the page size for this request only.

Constructor arguments:

- `ordering` - tuple of field names the queryset is sorted by, `-` prefix for
  descending. The first field is used to encode the cursor position and
  should be unique (or close to it) - a creation timestamp works well.
  Defaults to `("-pk",)` (`NINJA_PAGINATION_DEFAULT_ORDERING`).
- `page_size` - default page size. Defaults to `NINJA_PAGINATION_PER_PAGE`
  (100).
- `max_page_size` - upper bound for a client-supplied `page_size`. Defaults
  to `NINJA_MAX_PER_PAGE_SIZE` (100).

```python hl_lines="2"
@api.get("/users", response=list[UserSchema])
@paginate(CursorPagination, ordering=("date_joined", "id"), page_size=20)
def list_users(request):
    return User.objects.all()
```

Note that the response's items key is `results`, not `items` - `CursorPagination`
sets its own `items_attribute` (see [Output attribute](#output-attribute) below).

!!! note
    `NINJA_PAGINATION_MAX_OFFSET` (default 100) bounds the internal offset a
    cursor can encode, as a safeguard against malicious cursor values.

## Accessing pagination parameters in the view

Pass `pass_parameter` to receive the paginator's parsed `Input` in your view,
under whatever keyword name you choose:

```python hl_lines="2 4"
@api.get("/users", response=list[UserSchema])
@paginate(pass_parameter="pagination_info")
def list_users(request, **kwargs):
    limit = kwargs["pagination_info"].limit
    return User.objects.all()
```

`kwargs["pagination_info"]` is an instance of the paginator's `Input` schema -
so its available fields depend on the class in use (`.limit`/`.offset`,
`.page`/`.page_size`, or `.cursor`/`.page_size`).

## Async support

All built-in pagination classes support `async def` views transparently -
`@paginate` detects an async view and calls the paginator's
`apaginate_queryset()` instead of `paginate_queryset()`:

```python hl_lines="3"
@api.get("/users", response=list[UserSchema])
@paginate(LimitOffsetPagination)
async def list_users(request):
    return User.objects.all()
```

A custom pagination class needs to subclass `AsyncPaginationBase` and
implement `apaginate_queryset` to support async views - see
[Custom pagination classes](#custom-pagination-classes).

## Applying pagination to many operations at once

Use `RouterPaginated` instead of `Router` to automatically paginate every
operation on it whose `response` is a list, with no `@paginate` needed:

```python hl_lines="2 4 12 17"
from django.contrib.auth.models import Group
from ninja.pagination import RouterPaginated

router = RouterPaginated()


class GroupSchema(Schema):
    id: int
    name: str


@router.get("/users", response=list[UserSchema])
def list_users(request):
    return User.objects.all()


@router.get("/groups", response=list[GroupSchema])
def list_groups(request):
    return Group.objects.all()
```

Both operations are paginated with `NINJA_PAGINATION_CLASS`. An operation
that opts out just returns something other than a list, or applies its own
`@paginate(...)` explicitly.

To make this the behavior for the whole API, pass a `RouterPaginated` as
`default_router`:

```python hl_lines="3"
from ninja.pagination import RouterPaginated

api = NinjaAPI(default_router=RouterPaginated())


@api.get("/users", response=list[UserSchema])
def list_users(request):
    return User.objects.all()
```

## Custom pagination classes

Subclass `ninja.pagination.PaginationBase` and implement:

- `Input` - a `Schema` describing the parameters your paginator reads from
  the query string (e.g. a page number, or a limit/offset pair).
- `Output` - a `Schema` describing the page shape returned to the client
  (e.g. items plus a count, or items plus navigation links).
- `paginate_queryset(self, queryset, pagination, request, **params)` - given
  the operation's full queryset, `pagination` (a validated `Input` instance)
  and any of the arguments the view itself received, return the current
  page as a dict matching `Output`.

`Input`'s fields are always read from the query string, the same way the
built-in classes' `limit`/`offset`/`page`/`cursor` parameters are.

```python hl_lines="8 11 15 24"
from typing import Any

from ninja import Schema
from ninja.pagination import PaginationBase, paginate


class SkipPagination(PaginationBase):
    class Input(Schema):
        skip: int = 0

    class Output(Schema):
        items: list[Any]  # `items` is the default attribute
        total: int

    def paginate_queryset(self, queryset, pagination: Input, **params):
        skip = pagination.skip
        return {
            "items": queryset[skip : skip + 5],
            "total": self._items_count(queryset),
        }


@api.get("/users", response=list[UserSchema])
@paginate(SkipPagination)
def list_users(request):
    return User.objects.all()
```

`self._items_count(queryset)` is a helper on `PaginationBase` that calls
`.count()` when the queryset supports it and falls back to `len()` otherwise
- reuse it instead of writing that check yourself.

!!! tip
    The view's own arguments (including `request`) are available through
    `**params`:

    ```python
    def paginate_queryset(self, queryset, pagination: Input, **params):
        request = params["request"]
    ```

### Output attribute

Page items are placed under the `items` key by default. Override
`items_attribute` to use a different key - `CursorPagination`, for example,
sets it to `"results"`:

```python hl_lines="4 7"
class SkipPagination(PaginationBase):
    ...
    class Output(Schema):
        results: list[Any]
        total: int

    items_attribute: str = "results"
```

### Async custom pagination

Subclass `AsyncPaginationBase` instead, and implement `apaginate_queryset`
with the same signature - it's what `@paginate` calls for an `async def`
view:

```python hl_lines="4 15"
from ninja.pagination import AsyncPaginationBase


class SkipPagination(AsyncPaginationBase):
    class Input(Schema):
        skip: int = 0

    class Output(Schema):
        items: list[Any]
        total: int

    def paginate_queryset(self, queryset, pagination: Input, **params):
        ...  # sync views

    async def apaginate_queryset(self, queryset, pagination: Input, **params):
        skip = pagination.skip
        return {
            "items": [obj async for obj in queryset[skip : skip + 5]],
            "total": await self._aitems_count(queryset),
        }
```

`self._aitems_count(queryset)` is the async counterpart of `_items_count`.

!!! note
    A class that only defines `paginate_queryset` (i.e. plain
    `PaginationBase`) can't be used on an `async def` view - Django Ninja
    raises a `ConfigError` when it tries.
