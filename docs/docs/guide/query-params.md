# Query Parameters

Any function parameter that isn't part of the path, and isn't declared with a
`Body`, `Form`, `File`, `Header` or `Cookie` annotation, is read from the
request's query string.

## Basic usage

```python hl_lines="9"
from ninja import NinjaAPI

api = NinjaAPI()

WEAPONS = ["Ninjato", "Shuriken", "Katana", "Kama", "Kunai", "Naginata", "Yari"]


@api.get("/weapons")
def list_weapons(request, limit: int = 10, offset: int = 0):
    return WEAPONS[offset : offset + limit]
```

Calling this with `GET /api/weapons?offset=0&limit=10` gives you `limit=10` and
`offset=0` in the function, already converted to `int` and validated. Query
string values are always strings; **Django Ninja** parses and validates them
according to the type hint, the same way it does for [path
parameters](path-params.md):

- editor support (autocompletion, type checks)
- data parsing
- data validation
- automatic OpenAPI documentation

Since both `limit` and `offset` have defaults, they're optional: `GET
/api/weapons` is the same as `GET /api/weapons?offset=0&limit=10`, and `GET
/api/weapons?offset=20` gives you `offset=20` with `limit` still falling back
to its default of `10`.

!!! note
    An unannotated argument is treated as `str`:

    ```python
    @api.get("/weapons")
    def list_weapons(request, limit, offset):
        # limit and offset are both str
        ...
    ```

## Required and optional parameters

A parameter without a default value is required; one with a default value is
optional:

```python hl_lines="2"
@api.get("/weapons/search")
def search_weapons(request, q: str, offset: int = 0):
    results = [w for w in WEAPONS if q.lower() in w.lower()]
    return results[offset : offset + 10]
```

`GET /api/weapons/search` without `q` returns a `422` — `q` is required, while
`offset` falls back to `0` when it's missing.

To make a parameter optional without giving it a real default, use `None` and
a `X | None` annotation:

```python hl_lines="2"
@api.get("/weapons/search")
def search_weapons(request, q: str | None = None, offset: int = 0):
    if q is None:
        return WEAPONS[offset : offset + 10]
    return [w for w in WEAPONS if q.lower() in w.lower()][offset : offset + 10]
```

## Type conversion

Type hints drive both parsing and validation. This works for `str`, `int`,
`float`, `bool`, `UUID`, `date`, `datetime`, enums, and anything else Pydantic
knows how to parse:

```python hl_lines="6"
from datetime import date


@api.get("/example")
def example(
    request, s: str | None = None, b: bool | None = None, d: date | None = None
):
    return [s, b, d]
```

For `bool`, these query strings are accepted as `true` (case insensitive):

```
?b=1
?b=true
?b=on
?b=yes
```

...and these as `false`:

```
?b=0
?b=false
?b=off
?b=no
```

Anything else (`?b=random`) fails validation with a `422`, rather than
silently becoming `false`.

`date`/`datetime` accept both an ISO string and a Unix timestamp:

```
?d=2020-01-01
?d=1577836800
```

## Multiple values (lists)

A bare `list` annotation on a query parameter is treated as a request **body**
field, not a query one — so to collect repeated query keys (`?x=1&x=2&x=3`)
into a list, declare the parameter explicitly with `Query`:

```python hl_lines="4"
from ninja import Query

@api.get("/weapons/by-ids")
def weapons_by_ids(request, ids: list[int] = Query(...)):
    return [w for i, w in enumerate(WEAPONS) if i in ids]
```

`GET /api/weapons/by-ids?ids=1&ids=2&ids=3` gives `ids == [1, 2, 3]`. `Query()`
also accepts a default, so the list itself can be optional:

```python
@api.get("/weapons/by-ids")
def weapons_by_ids(request, ids: list[int] = Query([])):
    ...
```

## Grouping parameters into a Schema

For anything more than a couple of parameters, group them into a
[`Schema`](schemas.md) and annotate it with `Query`. Every field of the schema
is read from the query string, using each field's own type, default and
validation:

```python hl_lines="1-2 6-9 13"
from ninja import Query, Schema
from pydantic import Field


class Filters(Schema):
    limit: int = 100
    offset: int = 0
    query: str | None = None
    tags: list[str] = Field(None, alias="tag")


@api.get("/filter")
def filter_weapons(request, filters: Query[Filters]):
    return filters.model_dump()
```

`filters: Query[Filters]` is equivalent to `filters: Filters = Query(...)` —
use whichever reads better. A query schema can also be made optional as a
whole:

```python
@api.get("/filter")
def filter_weapons(request, filters: Filters | None = Query(None)):
    ...
```

You can mix a query schema with plain query parameters and other sources in
the same operation — **Django Ninja** merges them all before calling your
view. Note that a parameter typed with `Filters = Query(...)` has a real
default in the signature, so it can be placed after parameters that don't:

```python hl_lines="5"
@api.get("/filter-mixed")
def filter_mixed(
    request,
    page: int,
    filters: Filters = Query(...),
    sort: str = "name",
):
    return dict(page=page, sort=sort, **filters.model_dump())
```

For dynamic, database-driven filtering (building an ORM `Q` expression from a
schema), see [Filtering](filtering.md).

## Validation constraints

`Query()` accepts the same validation arguments as [path
parameters](path-params.md): `gt`, `ge`, `lt`, `le` for numbers,
`min_length`, `max_length`, `pattern` for strings, plus `title`, `description`,
`example`/`examples` and `deprecated` for the generated OpenAPI schema:

```python hl_lines="4-5"
@api.get("/weapons/page")
def weapons_page(
    request,
    limit: int = Query(10, gt=0, le=100),
    q: str | None = Query(None, min_length=3, max_length=50),
):
    return {"limit": limit, "q": q}
```

The same constraints can be set with a plain Pydantic `Field` when the
parameter is a field of a `Query` schema.

## Aliases

Use `alias` when the query key you need to accept isn't a valid Python
identifier, or simply differs from your parameter name:

```python hl_lines="2"
@api.get("/weapons/legacy")
def legacy_search(request, q: str = Query(..., alias="search-term")):
    return [w for w in WEAPONS if q.lower() in w.lower()]
```

`GET /api/weapons/legacy?search-term=kata` now maps to `q`. Inside a `Schema`,
set the alias with Pydantic's `Field(alias=...)`, as shown for `tags` above.

!!! tip
    Query parameters that aren't declared on the operation are ignored — you
    don't need to enumerate every possible key, only the ones you read.
