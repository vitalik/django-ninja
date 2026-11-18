# create_schema

`create_schema` is the function [`ModelSchema`](model-schema.md) uses internally to turn a
Django model into a `Schema` class at runtime. Reach for it when you need a schema *without*
declaring a class - for example when the field list is only known at runtime, or in a quick
script. For everyday API code, prefer `ModelSchema` - it's declarative and reads better in an
editor.

## Basic usage

```python
from django.contrib.auth.models import User
from ninja.orm import create_schema

UserSchema = create_schema(User)

# Equivalent to:
#
# class UserSchema(Schema):
#     id: Optional[int] = None
#     username: str
#     first_name: Optional[str] = None
#     last_name: Optional[str] = None
#     password: str
#     last_login: Optional[datetime] = None
#     is_superuser: bool = False
#     email: Optional[str] = None
#     ... and the rest of User's fields
```

!!! warning
    With no `fields` or `exclude`, `create_schema` includes **every** field on the model - this
    can accidentally expose something you didn't mean to (like a hashed password). Always pass
    `fields` or `exclude` explicitly.

Besides the model, `create_schema` takes:

- **`name`** - class name for the generated schema (defaults to the model's name).
- **`depth`** - how many levels deep to introspect related models (see [below](#relations-and-depth)).
- **`fields`** / **`exclude`** - which model fields to include ([below](#selecting-fields)).
- **`optional_fields`** - fields to make not-required ([below](#making-fields-optional)).
- **`custom_fields`** - extra or overridden fields ([below](#adding-or-overriding-fields)).
- **`base_class`** - the `Schema` subclass to build on ([below](#custom-base-class)).

## Selecting fields

`fields` and `exclude` are mutually exclusive - passing both raises a `ConfigError`.

### `fields`

Only the listed fields are added to the schema:

```python hl_lines="1"
UserSchema = create_schema(User, fields=["id", "username"])

# class UserSchema(Schema):
#     id: Optional[int] = None
#     username: str
```

### `exclude`

Every field **except** the listed ones is added:

```python hl_lines="1 2"
UserSchema = create_schema(
    User, exclude=["password", "last_login", "is_superuser", "user_permissions"]
)

# class UserSchema(Schema):
#     id: Optional[int] = None
#     username: str
#     first_name: Optional[str] = None
#     last_name: Optional[str] = None
#     email: Optional[str] = None
#     is_active: bool = True
#     date_joined: datetime
#     ...
```

## Relations and `depth`

By default, a `ForeignKey` or `ManyToManyField` becomes just the related object's primary key
(an `int` for a `list[int]`). `depth` tells `create_schema` to introspect that many levels into
related models instead, building a nested schema for them:

```python hl_lines="1 5"
UserSchema = create_schema(User, depth=1, fields=["username", "groups"])

# class UserSchema(Schema):
#     username: str
#     groups: list[Group]
```

`groups` became `list[Group]` - the `ManyToManyField` was introspected one level deeper and a
schema was generated for `Group` too, using **all** of its fields (the `fields`/`exclude` you
pass only apply to the top-level model):

```python
class Group(Schema):
    id: Optional[int] = None
    name: str
    permissions: list[int]  # depth is now exhausted, so back to plain pk list
```

Each extra level of `depth` costs one more level of nesting, so keep it small - it's easy to
pull in far more data (and far more queries) than you intended.

## Making fields optional

Pass `optional_fields` to make specific fields not required, regardless of whether they're
required on the model - handy for building a "patch" schema:

```python hl_lines="4"
PatchUserSchema = create_schema(
    User,
    fields=["username", "first_name", "last_name"],
    optional_fields=["first_name", "last_name"],
)
```

Use `"__all__"` to make every selected field optional at once:

```python hl_lines="4"
PatchUserSchema = create_schema(
    User,
    fields=["username", "first_name", "last_name"],
    optional_fields="__all__",
)
```

## Adding or overriding fields

`custom_fields` takes a list of `(name, type, default)` tuples. Use it to add a field that isn't
on the model, or to override the type/default `create_schema` picked for an existing one:

```python hl_lines="6-9"
from ninja import Field

UserSchema = create_schema(
    User,
    fields=["id", "username"],
    custom_fields=[
        ("full_name", str, None),                     # new field, not required, defaults to None
        ("id", str, Field(..., description="UUID")),  # override an existing field's type
    ],
)

# class UserSchema(Schema):
#     id: str
#     username: str
#     full_name: str = None
```

The third element can be a plain default value (`...` marks the field required; anything else -
including `None` - makes it optional to pass, using that as the default) or a `Field(...)`
instance when you need a description, alias or validation constraints too. A plain default
doesn't change the *type*: `("full_name", str, None)` still types the field as `str`, not
`Optional[str]`, so `full_name` may be omitted but passing `full_name=None` explicitly fails
validation. Type the field as `Optional[str]` (or `str | None`) instead if you need `None` itself
to be an accepted value.

## Custom name

By default the generated class is named after the model. Pass `name` to control it - useful
when you build several schemas from the same model and want the OpenAPI schema names to stay
readable:

```python
UserMinimalSchema = create_schema(User, name="UserMinimal", fields=["id", "username"])
```

If that name was already used by an earlier `create_schema` call - even for a different model -
a numeric suffix (`User2`, `User3`, ...) is appended automatically so class names never collide.

## Self-referencing schemas

A schema can reference itself the same way a hand-written [`Schema`](schemas.md#self-referencing-schemas)
does - quote the type and call `model_rebuild()` - but with `create_schema` the quoted name has
to match the `name` you passed in, since that's the name the class is rebuilt under:

```python hl_lines="3 6 9"
UserSchema = create_schema(
    User,
    name="UserSchema",  # required - model_rebuild() looks the class up by this name
    fields=["id", "username"],
    custom_fields=[
        ("manager", "UserSchema", None),
    ],
)
UserSchema.model_rebuild()
```

## Custom base class

`base_class` lets the generated schema inherit from your own `Schema` subclass instead of
`Schema` directly - handy for sharing a `model_config`, a validator, or extra methods across
every schema you generate:

```python hl_lines="4 6"
from ninja import Schema

class BaseSchema(Schema):
    model_config = {"str_strip_whitespace": True}

UserSchema = create_schema(User, fields=["id", "username"], base_class=BaseSchema)
```

## Schema caching

Calling `create_schema` twice with the exact same `model`, `name`, `depth`, `fields`, `exclude`,
`optional_fields` and `custom_fields` returns the **same** class instead of building a new one
each time - so it's cheap to call `create_schema` inside a function that runs on every request.
Change any of those arguments and you get a distinct class.

!!! note
    `base_class` isn't part of that cache key. If you call `create_schema` again with the same
    model and field selection but a different `base_class`, you'll get back the schema from the
    *first* call. Give calls that vary only by `base_class` their own `name` to avoid this.

## When to prefer ModelSchema

`create_schema` returns a class, but nothing about it is written down as a class in your code -
your editor and type checker only see `type[Schema]`. [`ModelSchema`](model-schema.md) builds the
exact same fields but as a real class definition, which means autocomplete, `isinstance` checks,
and the ability to add your own fields or `resolve_*` methods directly. Reach for `create_schema`
only when the model, field list or depth is decided at runtime rather than while you're writing
the code.
