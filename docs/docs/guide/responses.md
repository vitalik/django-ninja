# Responses

The `response` argument on an operation controls what an operation is allowed
to return: it validates the return value, serializes it, and documents its
shape in the OpenAPI schema. This page covers the different shapes `response`
can take; for how to define the schema classes themselves, see
[Schemas](schemas.md).

## Basic usage

Without a `response` argument, whatever you return is passed straight to the
renderer (JSON by default) with no validation at all:

```python
from ninja import NinjaAPI

api = NinjaAPI()


@api.get("/ping")
def ping(request):
    return {"status": "ok"}
```

Pass a `Schema` class to validate and filter the output — only the fields
declared on the schema make it into the response, even if the returned object
has more:

```python hl_lines="6-8 11 13"
from ninja import NinjaAPI, Schema

api = NinjaAPI()


class UserOut(Schema):
    id: int
    username: str


@api.get("/users/{user_id}", response=UserOut)
def get_user(request, user_id: int):
    return {"id": user_id, "username": "sam", "password": "hunter2"}
```

`password` is silently dropped — the response is `{"id": ..., "username": "sam"}`.

For a list endpoint, wrap the schema in `list[...]`:

```python hl_lines="11"
from ninja import NinjaAPI, Schema

api = NinjaAPI()


class UserOut(Schema):
    id: int
    username: str


@api.get("/users", response=list[UserOut])
def list_users(request):
    return [{"id": 1, "username": "sam"}, {"id": 2, "username": "alex"}]
```

!!! tip
    Nested schemas, aliases, resolvers, self-referencing schemas, and
    `FileField`/`ImageField` handling are all properties of the `Schema`
    class itself, not of `response=` — see [Schemas](schemas.md) for those.

## Returning querysets

You don't need to call `.all()` or wrap a queryset in `list()` before
returning it — validating against `list[Schema]` evaluates it for you:

```python hl_lines="11"
from ninja import NinjaAPI

from myapp.models import Task
from myapp.schemas import TaskSchema

api = NinjaAPI()


@api.get("/tasks", response=list[TaskSchema])
def tasks(request):
    return Task.objects.all()
```

!!! warning "Async views"
    This shortcut runs the query synchronously during validation, which
    Django forbids inside an `async def` view. Evaluate the queryset
    yourself first, e.g. with `asgiref.sync.sync_to_async`:

    ```python hl_lines="1 5 6"
    from asgiref.sync import sync_to_async


    @api.get("/tasks", response=list[TaskSchema])
    async def tasks(request):
        return await sync_to_async(list)(Task.objects.all())
    ```

    See [Async Support](async.md) for more on calling the ORM from async code.

## Multiple response schemas

An operation often needs more than one possible response — a success body,
plus a different body per error case. Pass `response` a `dict` mapping each
HTTP status code to the schema for that code:

```python hl_lines="3 17 20 22 23"
from datetime import datetime

from ninja import NinjaAPI, Schema, Status

api = NinjaAPI()


class Token(Schema):
    token: str
    expires: datetime


class Message(Schema):
    message: str


@api.post("/login", response={200: Token, 401: Message, 402: Message})
def login(request, username: str, password: str):
    if username != "admin":
        return Status(401, {"message": "Unauthorized"})
    if password != "hunter2":
        return Status(402, {"message": "Payment required"})
    return Status(200, {"token": "xyz", "expires": datetime.now()})
```

Return a `Status(status_code, value)` to tell **Django Ninja** which status
you're sending and which of the declared schemas to validate `value` against.
The status you set is also applied to the actual HTTP response.

!!! warning "Deprecated: returning a `(status_code, body)` tuple"
    Older code may return a plain 2-tuple instead of `Status(...)` — it still
    works, but raises a `DeprecationWarning` and will be removed in a future
    release:

    ```python
    return 401, {"message": "Unauthorized"}  # deprecated, use Status(401, ...)
    ```

!!! tip "Only one status code declared"
    If `response` names exactly one status code and it isn't `200` — e.g.
    `response={201: TaskOut}` — that code is used automatically, even for a
    plain `return task` with no `Status(...)` wrapper.

If a returned status code isn't declared in `response` at all (and there's no
`...` fallback — see below), **Django Ninja** raises a `ConfigError`.

## Response code ranges

Repeating the same schema for several codes gets tedious. Group them instead,
either with one of the built-in ranges:

```python hl_lines="1 4"
from ninja.responses import codes_4xx


@api.post("/login", response={200: Token, codes_4xx: Message})
def login(request, username: str, password: str):
    ...
```

```python
from ninja.responses import codes_1xx  # 100-101
from ninja.responses import codes_2xx  # 200-206
from ninja.responses import codes_3xx  # 300-308
from ninja.responses import codes_4xx  # 400-412, 416, 418, 425, 429, 451
from ninja.responses import codes_5xx  # 500-504
```

or with your own `frozenset` of codes:

```python hl_lines="1 4"
my_codes = frozenset({410, 429})


@api.post("/login", response={200: Token, my_codes: Message})
def login(request, username: str, password: str):
    ...
```

Finally, `...` (`Ellipsis`) matches **any** status code not otherwise listed
— handy as a catch-all:

```python hl_lines="1"
@api.get("/status", response={200: Token, ...: Message})
def status(request, code: int):
    return Status(code, {"message": "unexpected"})
```

!!! note
    A `...` fallback is excluded from the generated OpenAPI schema and docs
    UI, since there's no single status code to describe it under.

## Empty responses

For a response that has no body — [204 No Content](https://developer.mozilla.org/en-US/docs/Web/HTTP/Status/204),
for instance — map that status code to `None`:

```python hl_lines="1 3"
@api.post("/tasks/{task_id}", response={204: None})
def delete_task(request, task_id: int):
    return Status(204, None)
```

## Returning a Django `HttpResponse`

Return a Django `HttpResponse` (or any subclass, e.g. `redirect(...)`)
directly and **Django Ninja** passes it through untouched — no validation,
no `response=` schema involved:

```python hl_lines="10 15"
from django.http import HttpResponse
from django.shortcuts import redirect
from ninja import NinjaAPI

api = NinjaAPI()


@api.get("/plain")
def plain_text(request):
    return HttpResponse("some data", content_type="text/plain")


@api.get("/old-path")
def moved(request):
    return redirect("/new-path")
```

## Related

- To set a header, cookie, or status code on the response while still
  returning your normal data, see
  [Headers, Cookies & Temporal Response](temporal-response.md).
- For validation-error and exception responses, see
  [Errors & Exception Handling](errors.md).
- To change *how* a response body is encoded (JSON by default), see
  [Renderers](renderers.md).
- `by_alias`, `exclude_unset`, `exclude_defaults` and `exclude_none` tune how
  a `response=` schema is serialized — see [Operations](operations.md#by_alias-exclude_unset-exclude_defaults-exclude_none).
