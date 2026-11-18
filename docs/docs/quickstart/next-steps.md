# Auth, Routers & Next Steps

The events API works, but it all lives in one file and anyone can change data. On this page you'll move the endpoints into the `events` app, require login for writes, and let signed-in users register for events.

## Move the endpoints into a router

A `Router` is a group of endpoints that you mount on the API under a prefix, much like Django's `include()`. Each app can own its endpoints and the project just wires them together.

First, move the schemas to `events/schemas.py`, unchanged: `EventIn`, `EventOut` and `EventFilter`. Then `events/api.py` gets the endpoints, with `@api` replaced by `@router` and `/events` dropped from the paths:

```python title="events/api.py"
from ninja import Router

router = Router(tags=["events"])


@router.get("/", response=list[EventOut])
@paginate
def list_events(request, filters: Query[EventFilter]):
    ...


@router.get("/{event_id}", response=EventOut)
def get_event(request, event_id: int):
    ...

# ... and the rest
```

`mysite/api.py` is now only wiring:

```python title="mysite/api.py" hl_lines="3 7"
from ninja import NinjaAPI

from events.api import router as events_router

api = NinjaAPI()

api.add_router("/events", events_router)
```

The router's `/` becomes `/api/events/` and `/{event_id}` becomes `/api/events/{event_id}`. Thanks to `tags=["events"]`, the interactive docs now group these endpoints under an **events** heading. Routers can be nested, and each one can carry its own auth, tags and other settings. See [Routers](../guide/routers.md).

## Registrations

Add a model for "user X is going to event Y":

```python title="events/models.py"
from django.conf import settings


class Registration(models.Model):
    event = models.ForeignKey(Event, related_name="registrations", on_delete=models.CASCADE)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["event", "user"], name="unique_registration"),
        ]
```

and a schema for it, with the event **nested** inside:

```python title="events/schemas.py" hl_lines="2"
class RegistrationOut(ModelSchema):
    event: EventOut

    class Meta:
        model = Registration
        fields = ["id", "created_at"]
```

Declaring `event: EventOut` tells Django Ninja to serialize the related `Event` with `EventOut`, instead of returning only its id.

## Require login

Turn on auth for the whole API in `mysite/api.py`:

```python title="mysite/api.py" hl_lines="2 6"
from ninja import NinjaAPI
from ninja.security import django_auth

from events.api import router as events_router

api = NinjaAPI(auth=django_auth)

api.add_router("/events", events_router)
```

Every endpoint now requires a logged-in user, so you have to opt the public ones back out. Here's the complete `events/api.py`:

```python title="events/api.py" hl_lines="3 12 18-20 23 47-54"
from django.shortcuts import get_object_or_404
from ninja import Query, Router
from ninja.errors import HttpError
from ninja.pagination import paginate

from .models import Event, Registration
from .schemas import EventFilter, EventIn, EventOut, RegistrationOut

router = Router(tags=["events"])


@router.get("/", response=list[EventOut], auth=None)
@paginate
def list_events(request, filters: Query[EventFilter]):
    return filters.filter(Event.objects.order_by("starts_at"))


@router.get("/mine", response=list[RegistrationOut])
def my_registrations(request):
    return Registration.objects.filter(user=request.auth).select_related("event")


@router.get("/{event_id}", response=EventOut, auth=None)
def get_event(request, event_id: int):
    return get_object_or_404(Event, id=event_id)


@router.post("/", response={201: EventOut})
def create_event(request, payload: EventIn):
    return Event.objects.create(**payload.dict())


@router.put("/{event_id}", response=EventOut)
def update_event(request, event_id: int, payload: EventIn):
    event = get_object_or_404(Event, id=event_id)
    for attr, value in payload.dict().items():
        setattr(event, attr, value)
    event.save()
    return event


@router.delete("/{event_id}", response={204: None})
def delete_event(request, event_id: int):
    get_object_or_404(Event, id=event_id).delete()


@router.post("/{event_id}/register", response={201: RegistrationOut})
def register(request, event_id: int):
    event = get_object_or_404(Event, id=event_id)
    if event.registrations.filter(user=request.auth).exists():
        raise HttpError(409, "You are already registered for this event")
    if event.registrations.count() >= event.capacity:
        raise HttpError(409, "This event is full")
    return Registration.objects.create(event=event, user=request.auth)
```

What's new:

- **`NinjaAPI(auth=django_auth)`** requires a logged-in Django user for every endpoint, so new endpoints are protected unless you say otherwise. `django_auth` uses the regular Django session, the same one the admin uses.
- **`auth=None`** opts the two read endpoints back out, so anyone can browse events. Auth can be set on the whole API, on a router (`Router(auth=...)`) or on a single endpoint, and the most specific one wins.
- **`request.auth`** is whatever the authenticator returned. For `django_auth` that's the `User`.
- **`HttpError(409, "...")`** stops the request and returns that status with a JSON `{"detail": "..."}` body. There's no need to build error responses by hand.

An anonymous request to a protected endpoint gets a `401`:

```console
$ curl http://127.0.0.1:8000/api/events/mine
{"detail": "Unauthorized"}
```

To try it out, log in at `/admin/` and open `/api/docs`. Swagger UI reuses your session and sends the CSRF token for you, so you can register for an event with **Try it out**. `POST /api/events/1/register` returns the nested schema:

```json
{
    "event": {
        "id": 1,
        "title": "DjangoCon Europe",
        "city": "Dublin",
        "starts_at": "2027-04-23T09:00:00Z",
        "capacity": 50
    },
    "id": 1,
    "created_at": "2026-09-27T16:00:50.168Z"
}
```

Register a second time and you get `409 {"detail": "You are already registered for this event"}`.

!!! tip "Not using sessions?"
    `django_auth` suits browser clients on the same site. For mobile apps or other servers, use an API key or bearer token instead. It's a small class with one `authenticate()` method; see [Authentication](../guide/authentication.md).

## What you've built

In three pages, and without writing any serializers, URL patterns or docs by hand, you have an API with:

- typed, validated path, query and body parameters,
- schemas generated from Django models, including a nested one,
- full CRUD, pagination and filtering,
- session auth with public and protected endpoints,
- proper error responses, and
- interactive OpenAPI docs that always match the code.

## Where to go next

The [Tutorial](../tutorial/index.md) builds a larger project step by step. The [Guide](../guide/index.md) covers each feature in depth. Here's where to read more about everything used in this Quick Start:

| You used | Read more |
| --- | --- |
| `NinjaAPI`, `urls.py` | [NinjaAPI](../guide/api.md), [URLs & Reverse](../guide/urls.md) |
| `@api.get`, `@api.post`, ... | [Operations](../guide/operations.md) |
| `name: str`, `event_id: int` | [Query Parameters](../guide/query-params.md), [Path Parameters](../guide/path-params.md) |
| `payload: EventIn` | [Request Body](../guide/body.md), plus [Form Data](../guide/forms.md) and [File Uploads](../guide/files.md) |
| `ModelSchema`, nested schemas | [ModelSchema](../guide/model-schema.md), [Schemas](../guide/schemas.md) |
| `response={201: ...}` | [Responses](../guide/responses.md) |
| `@paginate` | [Pagination](../guide/pagination.md) |
| `FilterSchema` | [Filtering](../guide/filtering.md) |
| `Router`, `add_router` | [Routers](../guide/routers.md) |
| `auth=django_auth`, `request.auth` | [Authentication](../guide/authentication.md), [CSRF](../guide/csrf.md) |
| `HttpError` | [Errors & Exception Handling](../guide/errors.md) |
| `/api/docs` | [OpenAPI & Interactive Docs](../guide/openapi.md) |

Features you haven't seen yet: [async views](../guide/async.md), [throttling](../guide/throttling.md), [API versioning](../guide/versioning.md), [custom renderers](../guide/renderers.md) and a [test client](../guide/testing.md).
