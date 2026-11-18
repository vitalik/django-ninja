# Schema Configuration

`Schema` is a `pydantic.BaseModel`, so every Pydantic
[`model_config`](https://docs.pydantic.dev/latest/api/config/) option is available on it. This
page covers the handful that matter most day to day in Django Ninja — generating camelCase
output, rejecting unknown fields, and validating on assignment — plus how they interact with
`from_orm`/`from_attributes` and the operation-level `by_alias` argument.

## Setting config

Set `model_config` on the schema itself, exactly as you would on any Pydantic model:

```python hl_lines="5"
from pydantic import ConfigDict
from ninja import Schema

class UserSchema(Schema):
    model_config = ConfigDict(extra="forbid")
    id: int
    email: str
```

`Schema` itself sets `model_config = ConfigDict(from_attributes=True)` so it can read from
Django model instances as well as `dict`s. Pydantic **merges** a subclass's `model_config` with
what it inherits, so setting your own `model_config` doesn't lose `from_attributes` — you only
need to repeat it if you're deliberately turning it off.

`ModelSchema` and a class built with `create_schema()` are also `Schema` subclasses, so
`model_config` works the same way on those too.

## camelCase output with `alias_generator`

APIs consumed by JavaScript clients often use camelCase field names while the Python/Django side
stays `snake_case`. Pydantic's
[`alias_generator`](https://docs.pydantic.dev/latest/api/config/?query=alias_generator#pydantic.config.ConfigDict.alias_generator)
config option handles this — set it to a function that turns a field name into its alias, and
Pydantic ships a ready-made one for camelCase:

```python hl_lines="2 6"
from pydantic import ConfigDict
from pydantic.alias_generators import to_camel
from ninja import Schema

class UserSchema(Schema):
    model_config = ConfigDict(alias_generator=to_camel)
    id: int
    is_staff: bool
```

Two more things are required to actually get camelCase **in and out**:

- **`populate_by_name=True`** on the schema — without it, the schema only accepts the alias
  (`isStaff`) as input, which breaks `from_orm()`/`from_attributes` since Django objects and
  dicts are still keyed by the original `is_staff`.
- **`by_alias=True`** on the operation (or on a `Router`, which applies to every operation
  registered on it) — without it, serialization uses the plain field names regardless of
  `alias_generator`. See [Responses](responses.md) for where else `by_alias` can be set.

```python hl_lines="7-10 17"
from pydantic import ConfigDict
from pydantic.alias_generators import to_camel
from django.contrib.auth.models import User
from ninja import NinjaAPI, ModelSchema

class UserSchema(ModelSchema):
    model_config = ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True,  # required for from_orm() to still accept is_staff
    )
    class Meta:
        model = User
        fields = ["id", "email", "is_staff"]

api = NinjaAPI()

@api.get("/users", response=list[UserSchema], by_alias=True)
def get_users(request):
    return User.objects.all()
```

```json
[
  {"id": 1, "email": "tim@apple.com", "isStaff": true},
  {"id": 2, "email": "sarah@smith.com", "isStaff": false}
]
```

!!! tip
    `pydantic.alias_generators` also ships `to_pascal` and `to_snake`, and you can pass any
    plain function — `alias_generator=lambda field_name: field_name.upper()` works too.

## Rejecting unknown fields with `extra`

By default (Pydantic's own default, `extra="ignore"`), a `Schema` used as a request body
silently drops any field in the payload that isn't declared. Set `extra="forbid"` to reject
those requests instead:

```python hl_lines="5"
from pydantic import ConfigDict
from ninja import NinjaAPI, Schema

class TaskIn(Schema):
    model_config = ConfigDict(extra="forbid")
    title: str
    is_completed: bool = False

api = NinjaAPI()

@api.post("/tasks")
def create_task(request, payload: TaskIn):
    ...
```

Posting `{"title": "Write docs", "typo_field": true}` to this operation now fails with a `422`
and a Pydantic `extra_forbidden` error for `typo_field`, instead of the extra key being
silently discarded. The third option, `extra="allow"`, keeps unknown fields around and makes
them accessible as regular attributes on the validated instance.

`extra` is checked against incoming data, so it matters for schemas used as a request `Body`,
`Query`, etc. — it has no effect on what a `response=` schema *outputs*, since serialization
only ever emits the fields the schema declares.

## Validating on assignment with `validate_assignment`

Pydantic doesn't re-run validation when you set an attribute on an already-constructed instance,
by default — `validate_assignment=True` turns that on:

```python hl_lines="5"
from pydantic import ConfigDict
from ninja import Schema

class TaskIn(Schema):
    model_config = ConfigDict(validate_assignment=True)
    title: str

task = TaskIn(title="Write docs")
task.title = "Write docs "  # revalidated and stored
task.title = 123  # raises pydantic.ValidationError
```

This is most useful for a schema you build up or mutate after construction — for example one
you pass through a chain of helper functions before returning it as a `response=`.

## Other Pydantic config

Everything else in Pydantic's [`ConfigDict`](https://docs.pydantic.dev/latest/api/config/) —
`str_strip_whitespace`, `str_to_lower`, `frozen`, `title`, `json_schema_extra`, and the rest —
works the same on a `Schema` as it does on a plain `BaseModel`; nothing about Django Ninja
changes their behavior.

## Edge cases & tips

- **`model_config` merges up the inheritance chain** — a subclass only needs to set the keys it
  wants to change, as shown above for `from_attributes`.
- **`populate_by_name` is what makes `alias_generator` compatible with `from_orm()`.** Without
  it, validating from a Django object or a plain dict (both still keyed by the original field
  names) fails with a "field required" error for every renamed field.
- **`by_alias` for output is set on the operation or `Router` — not on the schema.**
  `alias_generator` only defines *what* the alias is; whether it's actually used when rendering
  a response is a separate, per-operation switch. See [Responses](responses.md).
- **Incoming request bodies are always documented in OpenAPI using aliases**, independent of
  `by_alias` — that argument only affects response serialization (and its OpenAPI schema).
- **`extra` only governs validation (input), not serialization (output).** Use `fields`/`exclude`
  on [`ModelSchema`](model-schema.md), or simply don't declare the field, to control what a
  response includes.
