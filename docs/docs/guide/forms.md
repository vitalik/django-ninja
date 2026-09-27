# Form Data

To read `application/x-www-form-urlencoded` or `multipart/form-data` data —
the way an HTML `<form>` submits — annotate a parameter with `Form`, the same
way you'd use [`Query`](query-params.md) or [`Path`](path-params.md). Django
Ninja reads it from `request.POST`, parses it according to the type hint and
validates it, same as any other parameter source.

## Basic usage

```python hl_lines="1 7"
from ninja import NinjaAPI, Form

api = NinjaAPI()


@api.post("/login")
def login(request, username: Form[str], password: Form[str]):
    return {"username": username, "password": "*****"}
```

`Form[str]` is shorthand for `username: str = Form(...)` — use whichever
reads better:

```python hl_lines="2"
@api.post("/login")
def login(request, username: str = Form(...), password: str = Form(...)):
    return {"username": username, "password": "*****"}
```

A default value makes the field optional:

```python
@api.post("/login")
def login(request, remember_me: bool = Form(False)):
    return {"remember_me": remember_me}
```

## Grouping parameters into a Schema

In the same way as [`Query`](query-params.md#grouping-parameters-into-a-schema)
or [`Body`](body.md), group related form fields into a `Schema` and annotate
it with `Form`:

```python hl_lines="14"
from ninja import Form, NinjaAPI, Schema

api = NinjaAPI()


class Item(Schema):
    name: str
    description: str | None = None
    price: float
    quantity: int


@api.post("/items")
def create(request, item: Form[Item]):
    return item
```

Every field of `Item` is read from the request's form fields, using each
field's own type, default and validation.

## Combining with path and query parameters

You can declare form fields alongside path and query parameters on the same
operation — Django Ninja resolves each function parameter from its own source
(path, query, form, ...) and calls your view with all of them:

```python hl_lines="14"
from ninja import Form, NinjaAPI, Schema

api = NinjaAPI()


class Item(Schema):
    name: str
    description: str | None = None
    price: float
    quantity: int


@api.post("/items/{item_id}")
def update(request, item_id: int, q: str, item: Form[Item]):
    return {"item_id": item_id, "item": item.dict(), "q": q}
```

Here `item_id` is taken from the path, `q` from the query string, and `item`
from the form fields — all in the same call.

## Validation constraints

`Form()` accepts the same validation arguments as
[`Query`](query-params.md#validation-constraints): `gt`, `ge`, `lt`, `le` for
numbers, `min_length`, `max_length`, `pattern` for strings, plus `title`,
`description`, `example`/`examples`, `deprecated` and `include_in_schema` for
the generated OpenAPI schema.

```python hl_lines="4-5"
@api.post("/items/quick")
def create_quick(
    request,
    name: str = Form(..., min_length=1, max_length=100),
    quantity: int = Form(1, gt=0),
):
    return {"name": name, "quantity": quantity}
```

The same constraints can be set with a plain Pydantic `Field` when the
parameter is a field of a `Form` schema.

## Aliases

Use `alias` when the form field name isn't a valid Python identifier, or
simply differs from your parameter name:

```python hl_lines="2"
@api.post("/items/legacy")
def create_legacy(request, name: str = Form(..., alias="item-name")):
    return {"name": name}
```

Inside a `Schema`, set the alias with Pydantic's `Field(alias=...)` instead.

## Mapping empty form fields to a default

HTML forms often submit optional fields as an empty string rather than
omitting them, which fails validation for a type such as `int`, `float` or
`bool`. Fix this with a wrap validator that falls back to the field's default
whenever the incoming value is an empty string — see the Pydantic docs on
[wrap validators](https://docs.pydantic.dev/latest/concepts/validators/#field-wrap-validator):

```python hl_lines="13-16 19 25-27"
from typing import Annotated, TypeVar

from pydantic import WrapValidator
from pydantic_core import PydanticUseDefault

from ninja import Form, NinjaAPI, Schema

api = NinjaAPI()

T = TypeVar("T")


def _empty_str_to_default(v, handler, info):
    if isinstance(v, str) and v == "":
        raise PydanticUseDefault
    return handler(v)


EmptyStrToDefault = Annotated[T, WrapValidator(_empty_str_to_default)]


class Item(Schema):
    name: str
    description: str | None = None
    price: EmptyStrToDefault[float] = 0.0
    quantity: EmptyStrToDefault[int] = 0
    in_stock: EmptyStrToDefault[bool] = True


@api.post("/items-blank-default")
def create_with_defaults(request, item: Form[Item]):
    return item.dict()
```

Posting `price=""` and `quantity=""` now falls back to `0.0` and `0` instead
of failing validation.

## Combining with file uploads

If an operation declares `Form` fields (or plain `Body` fields) together with
one or more [`File`](files.md) parameters, Django Ninja automatically treats
the whole request as `multipart/form-data` — you don't need to do anything
differently:

```python hl_lines="1 7"
from ninja import File, Form, NinjaAPI, UploadedFile

api = NinjaAPI()


@api.post("/upload")
def upload(request, title: str = Form(...), file: UploadedFile = File(...)):
    return {"title": title, "size": file.size}
```

See [File Uploads](files.md) for everything about `File`, including multiple
files and validation.

!!! tip
    Form parameters that aren't declared on the operation are ignored — you
    don't need to enumerate every field the client might send, only the ones
    you read.
