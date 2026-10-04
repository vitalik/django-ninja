# ModelSchema

`ModelSchema` is a [`Schema`](schemas.md) subclass that generates its fields directly from a
Django model, so you don't have to duplicate every field name and type by hand.

## Basic usage

Set `model` and `fields` on an inner `Meta` class:

```python hl_lines="5-7"
from django.contrib.auth.models import User
from ninja import ModelSchema

class UserSchema(ModelSchema):
    class Meta:
        model = User
        fields = ["id", "username", "first_name", "last_name"]

# Equivalent to:
#
# class UserSchema(Schema):
#     id: Optional[int] = None
#     username: str
#     first_name: Optional[str] = None
#     last_name: Optional[str] = None
```

For each field, `ModelSchema` looks at the Django field type to pick a Python type, and copies
over `null`/`blank` (→ optional with a `None` default), `default`, `help_text` (→ description)
and `verbose_name` (→ title).

!!! note
    `model` also accepts a string in `"app_label.ModelName"` form, e.g. `model = "auth.User"` -
    handy when you want to avoid importing the model directly.

## Selecting fields

`fields` and `exclude` are mutually exclusive - use whichever is shorter for your case.

### All fields

Pass `"__all__"` to include every field on the model:

```python hl_lines="4"
class UserSchema(ModelSchema):
    class Meta:
        model = User
        fields = "__all__"
```

!!! warning
    Using `"__all__"` is not recommended - it can accidentally expose fields you didn't mean to
    (like a hashed password). Prefer an explicit `fields` list.

### Excluding fields

To take every field **except** a few, use `exclude` instead:

```python hl_lines="4"
class UserSchema(ModelSchema):
    class Meta:
        model = User
        exclude = ["password", "last_login", "user_permissions"]

# Will create a schema with all the remaining fields:
#
# class UserSchema(Schema):
#     id: Optional[int] = None
#     username: str
#     first_name: Optional[str] = None
#     last_name: Optional[str] = None
#     email: Optional[str] = None
#     is_superuser: bool = False
#     ... and the rest
```

One of `fields` or `exclude` is required - `ModelSchema` refuses to build a schema without either
(to avoid silently exposing every field whenever a model gains a new one).

## Relations

Foreign keys and many-to-many fields are supported out of the box:

- A `ForeignKey` becomes the type of the related model's primary key (`int` by default).
- A `ManyToManyField` becomes a `list` of that primary-key type.

```python hl_lines="9-10"
from django.contrib.auth.models import User
from django.db import models
from ninja import ModelSchema

class Tag(models.Model):
    name = models.CharField(max_length=50)

class Comment(models.Model):
    author = models.ForeignKey(User, on_delete=models.CASCADE)
    tags = models.ManyToManyField(Tag)
    text = models.TextField()

class CommentSchema(ModelSchema):
    class Meta:
        model = Comment
        fields = ["id", "author", "tags", "text"]

# author: int   (the related User's pk)
# tags: list[int]
```

When you return a model instance as the response, Ninja resolves `author` and each item in
`tags` to their primary key automatically. If you need the related object's own fields nested
in the response instead of just its id, declare that field explicitly with another schema (see
[Overriding and adding fields](#overriding-and-adding-fields)), or build one with
[`create_schema(..., depth=...)`](create-schema.md).

## Making fields optional

For `PATCH`-style endpoints you often want every field optional regardless of what's required on
the model. Use `fields_optional`:

```python hl_lines="7"
from django.contrib.auth.models import Group

class PatchGroupSchema(ModelSchema):
    class Meta:
        model = Group
        fields = ["id", "name"]  # name is required on the model
        fields_optional = "__all__"
```

Or optionally make only a subset optional:

```python
fields_optional = ["name"]
```

When applying a patch payload to an instance, use `exclude_unset=True` so that fields the client
didn't send aren't reset to `None`:

```python hl_lines="6"
@api.patch("/patch/{pk}", response=PatchGroupSchema)
def patch(request, pk: int, payload: PatchGroupSchema):
    obj = get_object_or_404(Group, pk=pk)

    # Notice `exclude_unset=True` - only fields present in the request are applied
    for attr, value in payload.dict(exclude_unset=True).items():
        setattr(obj, attr, value)

    obj.save()
    return obj
```

### PatchDict

`PatchDict` is a shortcut for the same pattern: wrap any `Schema` in `PatchDict[...]` to get a
version where every field is optional, and the *validated* payload comes back as a plain `dict`
containing only the fields that were actually sent - no manual `fields_optional` or
`exclude_unset` needed.

```python hl_lines="1 10"
from ninja import NinjaAPI, PatchDict, Schema

class GroupSchema(Schema):
    # fields don't need to be declared Optional - PatchDict takes care of that
    name: str

api = NinjaAPI()

@api.patch("/groups/{pk}", response=GroupSchema)
def update_group(request, pk: int, payload: PatchDict[GroupSchema]):
    obj = get_object_or_404(Group, pk=pk)

    for attr, value in payload.items():
        setattr(obj, attr, value)

    obj.save()
    return obj
```

Here `payload` is a `dict` validated against `GroupSchema`, containing only the keys present in
the request body.

## Overriding and adding fields

To change the type of a generated field, or add a field that doesn't exist on the model, declare
it as a normal annotated attribute - it takes priority over whatever `ModelSchema` would have
generated:

```python hl_lines="1-4 8"
class GroupSchema(ModelSchema):
    class Meta:
        model = Group
        fields = ["id", "name"]


class UserSchema(ModelSchema):
    groups: list[GroupSchema] = []

    class Meta:
        model = User
        fields = ["id", "username", "first_name", "last_name"]
```

This is also how you nest a related object's full schema instead of just its primary key (see
[Relations](#relations) above), and how you attach validators, defaults or a different type to
any individual field.

Methods work as usual too - a `ModelSchema` is still a regular `Schema`/Pydantic model:

```python hl_lines="6-7"
class UserSchema(ModelSchema):
    class Meta:
        model = User
        fields = ["id", "username"]

    def greet(self) -> str:
        return f"Hello, {self.username}!"
```

## Custom field types

For each Django field, `ModelSchema` maps the field's internal type (`Field.get_internal_type()`)
to a Python type. This covers all the built-in Django field types, but if you use a field type it
doesn't know about (a custom field, or one from a third-party package), you'll get a `ConfigError`
telling you to register it:

```python hl_lines="6 11"
# models.py
from django.db import models
import pgvector

class MyModel(models.Model):
    embedding = pgvector.VectorField()

# schemas.py
from ninja.orm import register_field

register_field("VectorField", list[float])
```

`register_field` takes the Django field's internal type name (a string) and the Python type to
use for it, and only needs to run once (e.g. at import time in your `schemas.py`) before any
`ModelSchema` that uses that field type is defined.

## Edge cases & tips

- **`fields` and `exclude` can't be combined** - pick one per schema; mixing them raises a
  `ConfigError`.
- **Reverse relations are skipped.** Reverse foreign keys and reverse many-to-many accessors
  (the ones Django adds automatically, not a field you declared) are never included, even with
  `fields = "__all__"`; include them explicitly with your own annotated field if you need them.
- **`TextField.max_length`** is a form-level hint in Django, not a database constraint, so
  Ninja enforces it only on incoming request data, not when serializing an existing (possibly
  longer) value in a response.
- **Schema caching.** Identical calls with the same model, name, fields, excludes and optional
  fields reuse the same generated class rather than rebuilding it, so defining the same
  `ModelSchema` twice (e.g. in tests) is cheap.
- Prefer `ModelSchema` when a schema should track a model's fields declaratively; reach for
  [`create_schema()`](create-schema.md) instead when you need to build a schema dynamically at
  runtime (e.g. the model or field list is only known at call time).
