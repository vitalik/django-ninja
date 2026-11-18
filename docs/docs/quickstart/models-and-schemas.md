# Models & Schemas

On this page you'll turn a Django model into a complete CRUD API, then add pagination and filtering. Along the way you'll see how schemas are generated from your models.

## The model

Nothing Ninja-specific here, just a regular Django model in `events/models.py`:

```python title="events/models.py"
from django.db import models


class Event(models.Model):
    title = models.CharField(max_length=200)
    city = models.CharField(max_length=100)
    starts_at = models.DateTimeField()
    capacity = models.PositiveIntegerField(default=50)

    def __str__(self):
        return self.title
```

```console
python manage.py makemigrations events
python manage.py migrate
```

## Schemas

A **schema** describes the shape of data going in or out of your API. Django Ninja schemas are [Pydantic](https://docs.pydantic.dev/) models: a class with type-annotated fields.

```python title="mysite/api.py"
from datetime import datetime

from ninja import Schema


class EventIn(Schema):
    title: str
    city: str
    starts_at: datetime
    capacity: int = 50


class EventOut(Schema):
    id: int
    title: str
    city: str
    starts_at: datetime
    capacity: int
```

`EventIn` is what clients send, and `EventOut` is what they get back. They're separate so a client can't set `id` (or, later, fields you'd rather keep private). `capacity` has a default, so it's optional in `EventIn`.

A schema doesn't have to match a model. You'll use plain `Schema` classes for anything that isn't a table: login payloads, computed results, aggregates.

### The same, generated from the model

When a schema mirrors a model, as these do, it only repeats what the model already says. `ModelSchema` reads the fields from the model instead:

```python title="mysite/api.py"
from ninja import ModelSchema

from events.models import Event


class EventIn(ModelSchema):
    class Meta:
        model = Event
        fields = ["title", "city", "starts_at", "capacity"]


class EventOut(ModelSchema):
    class Meta:
        model = Event
        fields = ["id", "title", "city", "starts_at", "capacity"]
```

These two classes behave the same as the hand-written ones, with the types and the `capacity` default taken from the model. You also get the model's constraints: `title` is limited to 200 characters because of `max_length=200`. When you add or change a model field, the schema follows.

The rest of this Quick Start uses the `ModelSchema` versions. You can mix both kinds freely, and a `ModelSchema` can also declare extra fields of its own (see [ModelSchema](../guide/model-schema.md)).

## Read: list and detail

Use `response=` to tell Django Ninja what an endpoint returns:

```python title="mysite/api.py" hl_lines="1 4 9"
from django.shortcuts import get_object_or_404


@api.get("/events", response=list[EventOut])
def list_events(request):
    return Event.objects.all()


@api.get("/events/{event_id}", response=EventOut)
def get_event(request, event_id: int):
    return get_object_or_404(Event, id=event_id)
```

- You return **querysets and model instances directly**. Django Ninja reads the fields listed in the schema and serializes them to JSON. There's no serializer to call.
- `{event_id}` in the path becomes the `event_id: int` argument, converted and validated like the query parameters on the previous page.
- Django's `get_object_or_404` works as usual: a missing event is a `404` JSON response.
- Only the fields in `EventOut` are sent back, even if the object has more. The schema is also the contract shown in the docs.

`GET /api/events/1`:

```json
{
    "id": 1,
    "title": "DjangoCon Europe",
    "city": "Dublin",
    "starts_at": "2027-04-23T09:00:00Z",
    "capacity": 50
}
```

## Create, update, delete

A schema-typed argument is read from the **JSON request body**:

```python title="mysite/api.py" hl_lines="1-3 7"
@api.post("/events", response={201: EventOut})
def create_event(request, payload: EventIn):
    return Event.objects.create(**payload.dict())


@api.put("/events/{event_id}", response=EventOut)
def update_event(request, event_id: int, payload: EventIn):
    event = get_object_or_404(Event, id=event_id)
    for attr, value in payload.dict().items():
        setattr(event, attr, value)
    event.save()
    return event


@api.delete("/events/{event_id}", response={204: None})
def delete_event(request, event_id: int):
    get_object_or_404(Event, id=event_id).delete()
```

- `payload: EventIn` means "parse the body as `EventIn`". By the time your function runs, the data is valid and typed: `starts_at` is already a `datetime`.
- `response={201: EventOut}` maps a **status code to a schema**. With only one code listed, that's the code every response gets, so `create_event` returns `201` and `delete_event` returns `204` with an empty body.
- `update_event` mixes a path parameter and a body in one signature. Django Ninja works out where each argument comes from.

Send an incomplete body and the error lists every problem at once:

```json
{
    "detail": [
        {"type": "missing", "loc": ["body", "payload", "city"], "msg": "Field required"},
        {"type": "missing", "loc": ["body", "payload", "starts_at"], "msg": "Field required"}
    ]
}
```

Open `/api/docs` again. All five endpoints are there, with request and response schemas, and you can create an event from the browser with **Try it out**.

### More than one status code

When an endpoint can answer in different ways, list every status code in `response` and return `Status(code, data)` to pick one. For example, a `POST` that creates an event, or reports a clash with an existing one:

```python title="mysite/api.py" hl_lines="1 9 13 14"
from ninja import Schema, Status


class Conflict(Schema):
    message: str
    existing_id: int


@api.post("/events", response={201: EventOut, 409: Conflict})
def create_event(request, payload: EventIn):
    clash = Event.objects.filter(city=payload.city, starts_at=payload.starts_at).first()
    if clash:
        return Status(409, {"message": "Another event is already scheduled then", "existing_id": clash.id})
    return Status(201, Event.objects.create(**payload.dict()))
```

Each response is validated against the schema for its code, and both appear in the interactive docs. See [Responses](../guide/responses.md#multiple-response-schemas) for more.

!!! tip "Partial updates"
    For `PATCH`, where the client sends only the fields that change, use `PatchDict[EventIn]`. See [Request Body](../guide/body.md#partial-updates-with-patchdict).

## Pagination

A list endpoint that returns *every* row won't last long in production. Add one decorator:

```python title="mysite/api.py" hl_lines="1 5"
from ninja.pagination import paginate


@api.get("/events", response=list[EventOut])
@paginate
def list_events(request):
    return Event.objects.all()
```

The view still returns a plain queryset. `@paginate` adds `limit` and `offset` query parameters, slices the queryset in the database, and wraps the result:

```json
{
    "items": [{"id": 1, "title": "DjangoCon Europe", ...}],
    "count": 3
}
```

Page-number and cursor pagination, or your own class, are one argument away. See [Pagination](../guide/pagination.md).

## Filtering

Filters are also a schema: a `FilterSchema`, read from the query string. Each field maps to an ORM lookup:

```python title="mysite/api.py" hl_lines="10-17 22-23"
from typing import Annotated

from django.db.models import Q
from django.utils import timezone
from ninja import FilterLookup, FilterSchema, Query

...


class EventFilter(FilterSchema):
    search: Annotated[str | None, FilterLookup("title__icontains")] = None
    city: Annotated[str | None, FilterLookup("city__iexact")] = None
    upcoming: bool | None = None

    def filter_upcoming(self, value: bool) -> Q:
        now = timezone.now()
        return Q(starts_at__gte=now) if value else Q(starts_at__lt=now)


@api.get("/events", response=list[EventOut])
@paginate
def list_events(request, filters: Query[EventFilter]):
    return filters.filter(Event.objects.order_by("starts_at"))
```

- `search` and `city` map to `icontains` and `iexact` lookups.
- `upcoming` needs custom logic, so a `filter_upcoming` method returns a `Q` object.
- Filters left out of the request are skipped, and everything is validated. `?upcoming=maybe` gets a `422`, not a server error.

Now these all work, and combine with pagination:

```text
/api/events?city=dublin
/api/events?upcoming=true&search=django
/api/events?upcoming=true&limit=10&offset=20
```

See [Filtering](../guide/filtering.md) for combining filters with `OR`, filtering on related models, and more.

## What you have so far

About 60 lines of code give you a paginated, filterable, validated and documented CRUD API:

| Method | Path | |
| --- | --- | --- |
| `GET` | `/api/events` | list, with `search`, `city`, `upcoming`, `limit`, `offset` |
| `POST` | `/api/events` | create |
| `GET` | `/api/events/{event_id}` | detail |
| `PUT` | `/api/events/{event_id}` | update |
| `DELETE` | `/api/events/{event_id}` | delete |

Right now, though, anyone can create or delete events. Next: [Auth, Routers & Next Steps](next-steps.md).
