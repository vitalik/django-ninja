# Versioning

**Django Ninja** doesn't version individual operations — instead, you run one
`NinjaAPI` instance per version and mount each at its own URL prefix. This keeps every
version's schema, docs page and routing completely independent.

## Versioning with multiple `NinjaAPI` instances

Create a separate `NinjaAPI` instance for each version, giving each one its own
`version` and a distinct `urls_namespace` (the namespace defaults to `f"api-{version}"`,
so two different `version` strings already avoid a clash — see
[Namespaces](urls.md#namespaces-urls_namespace)):

```python hl_lines="3 4"
from ninja import NinjaAPI

api_v1 = NinjaAPI(version="1.0.0", urls_namespace="api-v1")
api_v2 = NinjaAPI(version="2.0.0", urls_namespace="api-v2")


@api_v1.get("/hello")
def hello_v1(request):
    return {"message": "Hello from V1"}


@api_v2.get("/hello")
def hello_v2(request):
    return {"message": "Hello from V2", "extra": "field"}
```

Then mount each one under its own prefix in **urls.py**:

```python hl_lines="6 7"
from django.urls import path
from myproject.api import api_v1, api_v2

urlpatterns = [
    ...
    path("api/v1/", api_v1.urls),
    path("api/v2/", api_v2.urls),
]
```

Each instance gets its own interactive docs and schema:

- `/api/v1/docs`
- `/api/v2/docs`

Since `version` and `title` only affect the generated OpenAPI schema and docs page
(see [Title, version and description](api.md#title-version-and-description)), nothing
stops you from using non-numeric version strings (`"beta"`, `"2024-01"`, ...) — Ninja
never parses `version` itself.

## Sharing routers between versions

A `Router` isn't tied to a particular `NinjaAPI`, so the same router can be mounted
into several versions at once. Each `add_router()` call clones the router's
operations onto that API (see [Routers](routers.md#tips)), so the mounts don't
interfere with each other:

```python hl_lines="14 15"
from ninja import NinjaAPI, Router

router = Router()


@router.get("/items")
def list_items(request):
    return [{"id": 1, "name": "Widget"}]


api_v1 = NinjaAPI(version="1.0.0", urls_namespace="api-v1")
api_v2 = NinjaAPI(version="2.0.0", urls_namespace="api-v2")

api_v1.add_router("/", router)
api_v2.add_router("/", router)
```

Because each `NinjaAPI` tracks its own set of mounted routers, this doesn't require a
`url_name_prefix` — that's only needed when the *same* router is mounted more than
once on the *same* API instance (see
[Mounting the same router twice](routers.md#mounting-the-same-router-twice)).

To evolve an endpoint for a new version without touching the old one, only mount the
shared router on `api_v1`, then register the new behavior directly on `api_v2` instead:

```python hl_lines="3 4 5 6"
api_v1.add_router("/", router)

# v2 only: same path, new response shape
@api_v2.get("/items")
def list_items_v2(request):
    return {"results": [{"id": 1, "name": "Widget"}], "count": 1}
```

Operations registered directly on `api_v2` are added to `api_v2.default_router`, which
is unrelated to `router`, so this doesn't affect `api_v1` at all.

## Versioning parts of an API

The same pattern works below the top level too — instead of two full APIs, mount a
versioned sub-tree of routers under one `NinjaAPI`:

```python
from ninja import NinjaAPI, Router

api = NinjaAPI()
items_v1 = Router()
items_v2 = Router()


@items_v1.get("/items")
def list_items_v1(request):
    return [{"id": 1}]


@items_v2.get("/items")
def list_items_v2(request):
    return {"results": [{"id": 1}], "count": 1}


api.add_router("/v1/", items_v1)
api.add_router("/v2/", items_v2)
```

This keeps a single schema and docs page (`/api/docs`) covering both versions, which
is usually simpler when the versions mostly share auth, throttling and exception
handlers — all of that is still configured once, on `api`.

## Different auth or business logic per instance

The same multi-instance setup is also how you'd split a public API from an internal
one, independent of versioning — see
[Multiple API instances](api.md#multiple-api-instances) for an example with different
`auth` per instance.

## Tips

- Ninja has no request-based versioning scheme (URL path converter, `Accept` header,
  query parameter, ...) built in — versioning is always a matter of which `NinjaAPI`
  or `Router` an operation is registered on, and which URL prefix that's mounted at.
- If two `NinjaAPI` instances end up with the same `version` (the default is always
  `"1.0.0"`), set `urls_namespace` explicitly on at least one of them, or `reverse()`
  won't be able to tell their operations apart. See
  [Namespaces](urls.md#namespaces-urls_namespace).
- `title` and `description` are shown on each version's own docs page, so it's worth
  setting them per instance (e.g. `NinjaAPI(title="My API", version="2.0.0")`) to make
  it obvious which version a visitor landed on.
- Routers must be added, and versions decided, before `api.urls` is first accessed —
  see [Adding routers](api.md#adding-routers).
