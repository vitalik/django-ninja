# Schemas

`Schema` is Django Ninja's own base class for describing the shape of data —
the fields a request body must contain, or the fields an operation's response
will expose. It's a `pydantic.BaseModel` subclass with a few Django-friendly
additions, and it's called `Schema` (rather than `Model`) purely to avoid
clashing with `django.db.models.Model`.

This page covers how to define a `Schema` class itself. To use one as a
request body see [Request Body](body.md); to use one as an operation's
`response=` see [Responses](responses.md).

## Defining a schema

A schema is a class that inherits from `ninja.Schema` with its fields
declared as type-annotated attributes, exactly like a Pydantic model:

```python hl_lines="4-7"
from ninja import Schema


class UserIn(Schema):
    username: str
    password: str
    is_active: bool = True
```

A field without a default, such as `username` and `password` above, is
**required**. A field with a default, such as `is_active`, is **optional** —
if it's missing from the input, the default is used instead. Use
`field: type | None = None` for a field that's optional and may explicitly be
`null`.

Any type Pydantic understands works here: `str`, `int`, `float`, `bool`,
`datetime.date` / `datetime.datetime`, `UUID`, `Decimal`, `Enum`, `list[...]`,
`dict[...]`, other `Schema` classes, and so on — see
[Pydantic's field types](https://docs.pydantic.dev/latest/concepts/types/)
for the full list.

It's common to use **different** schemas for what an operation accepts and
what it returns — for example, to keep a `password` field out of the
response:

```python hl_lines="12-14 17"
from django.contrib.auth.models import User
from ninja import NinjaAPI, Schema

api = NinjaAPI()


class UserIn(Schema):
    username: str
    password: str


class UserOut(Schema):
    id: int
    username: str


@api.post("/users", response=UserOut)
def create_user(request, data: UserIn):
    user = User.objects.create_user(data.username, password=data.password)
    return user
```

Django Ninja uses `UserOut` to validate and serialize whatever `create_user`
returns, and to generate its OpenAPI schema — which also means the response
is **limited** to the fields declared on `UserOut`, even if the returned
object (a Django `User` instance here) has other attributes.

## Nested schemas and lists

A schema field can be another `Schema`, to represent a nested object, or a
`list[...]` of one, to represent a collection:

```python hl_lines="15 18"
from ninja import NinjaAPI, Schema

api = NinjaAPI()


class OwnerSchema(Schema):
    id: int
    first_name: str


class TaskSchema(Schema):
    id: int
    title: str
    is_completed: bool
    owner: OwnerSchema | None = None


@api.get("/tasks", response=list[TaskSchema])
def tasks(request):
    return [
        {"id": 1, "title": "Write docs", "is_completed": False, "owner": {"id": 1, "first_name": "Sam"}},
        {"id": 2, "title": "Review PRs", "is_completed": False, "owner": None},
    ]
```

Nesting works from ORM objects too, not just dicts. Given a `Task` model with
a nullable `owner` foreign key, `TaskSchema` above validates straight off a
queryset — no dicts required:

```python hl_lines="8"
from django.contrib.auth.models import User
from django.db import models


class Task(models.Model):
    title = models.CharField(max_length=200)
    is_completed = models.BooleanField(default=False)
    owner = models.ForeignKey(User, null=True, on_delete=models.SET_NULL)
```

```python
@api.get("/tasks", response=list[TaskSchema])
def tasks(request):
    return Task.objects.select_related("owner")
```

```json hl_lines="3"
[
    {"id": 1, "title": "Write docs", "is_completed": false, "owner": {"id": 1, "first_name": "Sam"}},
    {"id": 2, "title": "Review PRs", "is_completed": false, "owner": null}
]
```

A task without an owner serializes `owner` as `null`, matching the
`OwnerSchema | None = None` field above.

!!! tip "Watch out for N+1 queries"
    Serializing `owner` touches `task.owner` for every task in the list —
    without `select_related("owner")` on the queryset, that's one extra
    query per task. Reach for `select_related` on a `ForeignKey` /
    `OneToOneField` like this one, and `prefetch_related` on a to-many or
    reverse relation, to fetch everything up front instead.

This also works through reverse relations. When the source value for a field
is a Django `Manager` or `QuerySet` (a `related_set`, for instance), Django
Ninja automatically evaluates it into a plain list before validation, so you
can type the field as `list[ChildSchema]` directly, without calling `.all()`
or wrapping it in `list()` yourself.

## Aliases

By default, a schema field is read from the identically-named attribute (or
dict key) on the object you're serializing. Give a field an
`alias` to read it from somewhere else instead — `Schema` extends Pydantic's
`Field(..., alias=...)` to also follow **dotted paths** and to **call**
attributes that turn out to be callable:

```python hl_lines="1 22-24"
from ninja import Field, Schema


class Owner:
    def __init__(self, first_name):
        self.first_name = first_name

    def get_title(self):
        return "owner"


class Task:
    def __init__(self, id, is_completed, owner):
        self.id = id
        self.is_completed = is_completed
        self.owner = owner


class TaskSchema(Schema):
    id: int
    # the first Field() argument is the default — use ... for a required field
    completed: bool = Field(..., alias="is_completed")
    owner_first_name: str = Field(None, alias="owner.first_name")
    owner_title: str = Field(None, alias="owner.get_title")  # called automatically


TaskSchema.from_orm(Task(id=1, is_completed=True, owner=Owner("Sam"))).dict()
# {"id": 1, "completed": True, "owner_first_name": "Sam", "owner_title": "owner"}
```

Dotted aliases are resolved with Django's template variable lookup, so they
also work against dict keys and list/tuple indexes along the path, for
example `alias="message_set.0.text"`.

The call-following behavior above is also the common way to expose a Django
`choices` field's display value — Django generates a `get_<field>_display()`
method for any field with `choices=`, so aliasing straight to it works
without a resolver:

```python hl_lines="3"
class TaskSchema(Schema):
    type: str
    type_display: str = Field(None, alias="get_type_display")
```

!!! note "Aliases and plain `dict` input"
    Dotted-path resolution only kicks in when the source object is **not** a
    `dict` — a `dict` source is only ever looked up by its exact top-level
    key. When you validate from a `dict` (as most request bodies do), use a
    plain, non-dotted `alias` if you need one.

## Resolvers

A resolver computes a field's value with a method named `resolve_<field>`
instead of reading it from an attribute or alias. It must be a `@staticmethod`
that takes the object being serialized as its only required argument:

```python hl_lines="7 9-11"
from ninja import Schema


class TaskSchema(Schema):
    id: int
    title: str
    lower_title: str

    @staticmethod
    def resolve_lower_title(obj):
        return obj.title.lower()
```

!!! warning "Resolvers must be `@staticmethod`"
    Only `@staticmethod` resolvers are currently supported. A resolver
    defined as a regular method (expecting `self`) raises
    `NotImplementedError` when it runs — always use `@staticmethod`.

A resolver overrides whatever value the object would otherwise supply for
that field — including one that also has a matching attribute — so it's also
a way to add a field that doesn't exist on the source object at all, as
`lower_title` does above.

### Accessing context

Pydantic v2's serialization/validation `context` is available to a resolver
too — add a `context` argument (or `**kwargs`) to receive it:

```python hl_lines="9-11"
from ninja import Schema


class TaskSchema(Schema):
    id: int
    path: str = ""

    @staticmethod
    def resolve_path(obj, context):
        request = context["request"]
        return request.path
```

When a schema like this is used as a `response=` for an operation, Django
Ninja automatically passes `{"request": request, "response_status": <code>}`
as the context — no setup required. The same applies the other way round: a
schema used as request input (a [body](body.md) parameter, for instance) is
validated with `{"request": request}` as its context, so a resolver or
validator on an input schema can read `context["request"]` too. Outside a
view, pass your own:

```python
TaskSchema.model_validate({"id": 1}, context={"request": my_request})
```

## Files and images

Django's `FileField` and `ImageField` are, by default, converted to their
`str` URL rather than serialized as objects. Given a model with
`image = models.ImageField(upload_to="images")`, just declare the matching
schema field as `str` (or `str | None`) and Django Ninja does the rest:

```python hl_lines="6"
from ninja import Schema


class PictureSchema(Schema):
    title: str
    image: str
```

Serializing an object whose `image` attribute is a `FieldFile` produces its
`.url` as a plain string, e.g. `"/media/images/zebra.jpg"`. If the field can
be empty, declare it `str | None` — an empty `FieldFile` then serializes to
`None` instead of failing validation; with a plain `str` field, an empty
value still raises a validation error.

## Self-referencing schemas

To create a schema that references itself — a tree of comments with
replies, for instance — put the type in quotes and call `model_rebuild()`
once the class is fully defined:

```python hl_lines="6 9"
from ninja import Schema


class Comment(Schema):
    text: str
    replies: "list[Comment] | None" = None


Comment.model_rebuild()  # required to resolve the quoted type above
```

!!! tip "Self-referencing a schema from `create_schema()`"
    A schema generated with [`create_schema()`](create-schema.md) needs the
    same treatment, but its class name must be passed explicitly via
    `create_schema(..., name="...")` so it's addressable for
    `model_rebuild()` — see [create_schema](create-schema.md).

## Schema vs. plain Pydantic models

`Schema` is a `pydantic.BaseModel` — every Pydantic feature (validators,
computed fields, `model_config`, serialization, JSON Schema...) is available
unchanged, and everything above works on top of it. The differences that
matter day to day:

- **`from_attributes=True` by default.** A plain Pydantic model has to opt
  into reading from objects with `model_config = ConfigDict(from_attributes=True)`;
  a `Schema` always can, in addition to reading from a `dict`.
- **Alias resolution is enhanced**, as covered above: dotted paths, list/dict
  indexing, and automatically calling callables (`Field(alias="get_x")`).
- **`Manager` and `QuerySet` attributes are auto-evaluated** into plain lists
  during serialization, so a to-many relation typed as `list[ChildSchema]`
  doesn't need an explicit `.all()`.
- **`FileField` / `ImageField` values become their `.url`** (or `None`, when
  the field is typed to allow it), as covered above.
- **Resolvers must be `@staticmethod`** — see above.
- A couple of Pydantic v1-style convenience methods are kept around:
  `.from_orm(obj)` is an alias for `.model_validate(obj)`, and `.dict()` is an
  alias for `.model_dump()`.

See [Schema Configuration](schema-config.md) for the `model_config` options
that matter most in Django Ninja (alias generators, `extra`, validation
modes), and [ModelSchema](model-schema.md) / [create_schema](create-schema.md)
for generating a `Schema` straight from a Django model instead of writing
one by hand.

## Serializing outside a view

Everything above also works directly, without going through an operation —
useful in management commands, signal handlers, or tests. `.from_orm()`
validates an object (or a queryset/list of them) into schema instances, and
`.dict()` / `.model_dump_json()` give you plain data back out:

```python
>>> class PersonSchema(Schema):
...     name: str
...
>>> person = Person.objects.get(id=1)
>>> data = PersonSchema.from_orm(person)
>>> data
PersonSchema(name='Mr. Smith')
>>> data.dict()
{'name': 'Mr. Smith'}
>>> [PersonSchema.from_orm(p).dict() for p in Person.objects.all()]
[{'name': 'Mr. Smith'}, {'name': 'Mrs. Smith'}]
```

!!! tip "`.schema()` is deprecated"
    If you're carrying over habits from Pydantic v1, use `.model_json_schema()`
    (or Ninja's own `.json_schema()`, which additionally cleans up the JSON
    Schema output for OpenAPI) — the old `.schema()` still works but emits a
    `DeprecationWarning`.
