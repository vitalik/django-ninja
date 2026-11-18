# URLs & Reverse

Every operation you register — directly on `NinjaAPI` or through a `Router` — becomes
a normal Django URL pattern with a name, mounted under a namespace. This page covers
how that path and name are built, and how to get them back with Django's `reverse()`.

## How paths are built

`api.urls` (or `router.urls_paths(...)` internally) joins the router's mount prefix
and each operation's path, using the same `{param}` notation you write in the
decorator:

```python
from ninja import NinjaAPI

api = NinjaAPI()


@api.get("/hello/{name}")
def hello(request, name: str):
    return {"message": f"Hello, {name}"}
```

Before handing the path to Django, Ninja rewrites `{name}` to Django's own converter
syntax (`<name>`, or `<int:id>` once you add a type — see
[Path Parameters](path-params.md)) and collapses any double slashes produced by
joining a router's prefix with an operation's path. So `add_router("/events/", router)`
with an operation path of `"/"` ends up as `events/`, not `events//`.

## Reversing operations by name

Every operation is registered under a Django URL *name* — by default the view
function's name — inside a namespace that defaults to `"api-" + version`
(`"api-1.0.0"` for a fresh `NinjaAPI()`):

```python
from django.urls import reverse
from ninja import NinjaAPI

api = NinjaAPI()


@api.get("/hello")
def hello(request):
    return {"message": "hello"}


hello_url = reverse("api-1.0.0:hello")  # "/api/hello"
```

This implicit name is just the view function's `__name__`. So stacking multiple
method decorators on the same function — `@api.get` and `@api.post` on the same
`items`, say — produces two separate URL patterns that happen to share that default
name. Give each operation its own `url_name` (see below) if you need to `reverse()`
them independently.

!!! tip
    Use `reverse_lazy` instead of `reverse` when you need the URL before Django has
    finished loading URLconfs — for example as a default value in a model field or a
    class attribute.

## Naming an operation explicitly

Pass `url_name` to any operation decorator (`get`, `post`, `put`, `patch`, `delete`,
`api_operation`) to use your own name instead of the function name:

```python hl_lines="6"
from ninja import NinjaAPI

api = NinjaAPI()


@api.get("/users", url_name="user_list")
def users(request):
    return []
```

```python
from django.urls import reverse

reverse("api-1.0.0:user_list")  # "/api/users"
```

An explicit `url_name` always wins over the auto-generated one, for every operation
type, including `Router`-level operations.

## Namespaces (`urls_namespace`)

The namespace comes from `NinjaAPI(urls_namespace=...)`, and defaults to
`f"api-{version}"`. Set it explicitly whenever you run more than one `NinjaAPI` with
the same `version` (the default is `"1.0.0"` for all of them), since `reverse()`
otherwise can't tell their operations apart:

```python hl_lines="3 4"
from ninja import NinjaAPI

api_public = NinjaAPI(urls_namespace="public_api")
api_private = NinjaAPI(urls_namespace="private_api")


@api_public.get("/users")
def public_users(request):
    return []


@api_private.get("/users")
def private_users(request):
    return []
```

```python
from django.urls import reverse

reverse("public_api:public_users")
reverse("private_api:private_users")
```

See [The NinjaAPI Instance](api.md) for mounting multiple `NinjaAPI` instances side by
side.

## Customizing name generation (`get_operation_url_name`)

For naming logic that should apply across an entire API — rather than passing
`url_name` on every single operation — override `get_operation_url_name` on a
`NinjaAPI` subclass:

```python hl_lines="5 6"
from ninja import NinjaAPI


class MyAPI(NinjaAPI):
    def get_operation_url_name(self, operation, router):
        return operation.view_func.__name__ + "_v2"


api = MyAPI()


@api.get("/hello")
def hello(request):
    return {"message": "hello"}
```

```python
from django.urls import reverse

reverse("api-1.0.0:hello_v2")
```

`get_operation_url_name` receives the `Operation` and the `Router` it's registered on,
and is only consulted when the operation itself didn't set `url_name` explicitly.
There's a sibling hook, `get_openapi_operation_id`, for the (unrelated) OpenAPI
`operationId` — see [The NinjaAPI Instance](api.md#subclassing-ninjaapi).

## Routers and `url_name_prefix`

Names must be unique within a namespace, so mounting the *same* `Router` instance
more than once — directly, or indirectly by nesting it under two different parents —
requires a distinct `url_name_prefix` for every mount after the first:

```python
from ninja import NinjaAPI, Router

things_router = Router()


@things_router.get("/")
def list_things(request):
    return []


api = NinjaAPI()
api.add_router("/v1/things/", things_router)
api.add_router("/v2/things/", things_router, url_name_prefix="things_v2")
```

```python
from django.urls import reverse

reverse("api-1.0.0:list_things")            # /v1/things/
reverse("api-1.0.0:things_v2_list_things")  # /v2/things/
```

Without `url_name_prefix` on the second `add_router()` call, this raises a
`ConfigError` immediately, right when that `add_router()` call is made.

!!! warning
    `url_name_prefix` is only applied to *auto-generated* names. If an operation sets
    `url_name` explicitly, mounting its router twice produces two URLs sharing that
    same name — Ninja won't prefix it for you, so pick a unique explicit name per
    mount yourself when you need one.

## Reserved names

Within a namespace, Ninja reserves a few names for itself: `openapi-json` and
`openapi-view` (added whenever `openapi_url` / `docs_url` are set — see
[The NinjaAPI Instance](api.md)), and `api-root` (the empty-path view used
internally to resolve nested mount prefixes). Avoid reusing these as an explicit
`url_name`.

## Tips

- There's no way to suppress URL naming entirely — every operation always ends up
  with a name, either the one you pass explicitly, the one `get_operation_url_name`
  returns, or (its default) the view function's `__name__`. Passing `url_name=""` has
  no effect; it's treated the same as not passing `url_name` at all.
- Add every operation and call every `add_router()` *before* anything accesses
  `api.urls` (Django does this once, the first time it needs your URLconf). Routers
  freeze at that point, and both adding operations to a frozen router and calling
  `add_router()` afterwards raise a `ConfigError`.
- `url_name` only has to be unique within its namespace, so operations on two
  different `NinjaAPI` instances (each with their own `urls_namespace`) can safely
  share the same name.
