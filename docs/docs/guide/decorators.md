# Decorators

Beyond [`auth=`](authentication.md), [`throttle=`](throttling.md) and the other
operation options, you can wrap operations with plain Python decorators — your own,
or ones from Django and third-party libraries. Attach one to a single operation with
`@decorate_view`, or to every operation in a `Router` or an entire `NinjaAPI` with
`add_decorator()`.

## VIEW vs OPERATION mode

Both `decorate_view` and `add_decorator()` can run your decorator in one of two
modes:

| Mode | Wraps | Runs | Receives | Returns |
|---|---|---|---|---|
| `"view"` | Ninja's whole request handler | before authentication, throttling and parameter parsing | the raw `HttpRequest` and unparsed URL kwargs, exactly like a normal Django view | a Django `HttpResponse` |
| `"operation"` (default) | your endpoint function itself | after parameters are parsed and validated, and auth/throttle checks pass | the same validated arguments your function normally receives | whatever your function returns (a dict, a `Schema`, a `(status, data)` tuple, …) — not yet turned into a response |

Use **VIEW** mode for anything that works at the HTTP level — caching, adding
headers, rate limiting, or reusing an existing Django view decorator such as
`cache_page` or `vary_on_headers`, which expect a real `(request) -> HttpResponse`
view. Use **OPERATION** mode when you need the validated, typed data your function
receives, or want to act on its raw return value before Ninja serializes it.

## `@decorate_view` — per-operation decorators

`decorate_view` applies one or more Django-view-style decorators to a single
operation. It always runs in VIEW mode:

```python
from django.views.decorators.cache import cache_page
from ninja import NinjaAPI
from ninja.decorators import decorate_view

api = NinjaAPI()


@api.get("/cached")
@decorate_view(cache_page(60 * 15))
def cached_endpoint(request):
    return {"data": "this response is cached for 15 minutes"}
```

`@decorate_view` can go above or below `@api.get(...)` / `@router.get(...)` — both
orders work the same way.

Pass several decorators to apply them all; they combine the same way stacked
`@decorators` would, with the **last argument ending up outermost**:

```python hl_lines="10"
from django.views.decorators.cache import cache_page
from django.views.decorators.vary import vary_on_headers
from ninja import NinjaAPI
from ninja.decorators import decorate_view

api = NinjaAPI()


@api.get("/multi")
@decorate_view(cache_page(300), vary_on_headers("User-Agent"))
def multi_decorated(request):
    return {"data": "cached and varied by User-Agent"}
```

Here `vary_on_headers` runs first (outermost) and `cache_page` runs right next to
Ninja's own handler — equivalent to writing `@vary_on_headers(...)` above
`@cache_page(...)`.

## `add_decorator()` — router and API-wide decorators

`Router.add_decorator()` and `NinjaAPI.add_decorator()` apply a decorator to every
operation registered on that router (or across the whole API), without touching each
operation individually:

```python
router.add_decorator(decorator, mode="operation")   # or mode="view"
api.add_decorator(decorator, mode="operation")
```

`mode` defaults to `"operation"`. An invalid value raises `ValueError`.

Router-level example — log every call, with access to the validated arguments:

```python hl_lines="14"
from ninja import Router

router = Router()


def log_operation(func):
    def wrapper(request, *args, **kwargs):
        print(f"Calling {func.__name__} with {kwargs}")
        return func(request, *args, **kwargs)

    return wrapper


router.add_decorator(log_operation)  # OPERATION mode, the default


@router.get("/users/{user_id}")
def get_user(request, user_id: int):
    return {"user_id": user_id}
```

API-level example — add a header to every response, in VIEW mode since it needs the
actual `HttpResponse`:

```python hl_lines="15"
from ninja import NinjaAPI

api = NinjaAPI()


def cors_headers(func):
    def wrapper(request, *args, **kwargs):
        response = func(request, *args, **kwargs)
        response["Access-Control-Allow-Origin"] = "*"
        return response

    return wrapper


api.add_decorator(cors_headers, mode="view")
```

You can call `add_decorator()` multiple times to stack several decorators on the
same router or API, and it doesn't matter whether you call it before or after
`add_router()` — everything is resolved once, when the API generates its URLs. It
must be called before that happens, though: adding a decorator to a router or API
that's already been used to generate URLs raises `ConfigError`.

## Reusable permission checks

Inline permission checks get repetitive once several endpoints need them. A
small decorator placed **below** `@api.<method>` wraps the endpoint function
itself, so it runs in OPERATION mode — after authentication and request
validation, once `request.auth` is already set:

```python hl_lines="14-15"
from functools import wraps

from ninja import NinjaAPI
from ninja.errors import HttpError
from ninja.security import django_auth

api = NinjaAPI()


def require_perm(perm: str):
    def decorator(func):
        @wraps(func)  # keeps the signature, so Ninja still parses the parameters
        def wrapper(request, *args, **kwargs):
            if not request.auth.has_perm(perm):
                raise HttpError(403, "Permission denied")
            return func(request, *args, **kwargs)

        return wrapper

    return decorator


@api.delete("/posts/{post_id}", auth=django_auth)
@require_perm("blog.delete_post")
def delete_post(request, post_id: int):
    return {"deleted": post_id}
```

`request.auth` is whatever your authenticator returned: a Django `User` for
`django_auth`, so any of its methods (`has_perm`, `has_perms`, `groups`, ...)
can drive the check. With a custom authenticator that returns e.g. a token or
API-key object, check that object's own fields instead.

To protect every operation on a router (or the whole API) at once, register
the same decorator with `add_decorator()`:

```python
from ninja import Router
from ninja.security import django_auth

router = Router(auth=django_auth)
router.add_decorator(require_perm("blog.view_post"))


@router.get("/posts")
def list_posts(request):
    return {"posts": []}
```

!!! note
    Decorators applied with `@decorate_view` or `add_decorator(..., mode="view")`
    run *before* authentication, so `request.auth` isn't available there yet —
    keep permission checks in OPERATION mode (the default), as shown above.

See [Authentication](authentication.md) for the full picture on `auth=` and
what `request.auth` holds for each built-in authenticator.

## Practical examples

A few compact, self-contained decorators showing each mode in action.

**Request timing** (OPERATION mode) — add a `_timing` field to any dict
response:

```python
import time
from functools import wraps

from ninja import Router

router = Router()


def timing_decorator(func):
    @wraps(func)
    def wrapper(request, *args, **kwargs):
        start = time.time()
        result = func(request, *args, **kwargs)
        if isinstance(result, dict):
            result["_timing"] = f"{time.time() - start:.3f}s"
        return result

    return wrapper


router.add_decorator(timing_decorator)


@router.get("/slow")
def slow_endpoint(request):
    time.sleep(1)
    return {"message": "done"}
# -> {"message": "done", "_timing": "1.001s"}
```

**Feature-flag gate** (OPERATION mode) — reject with a `(status, data)` tuple
instead of raising:

```python
from functools import wraps

from ninja import Router

router = Router()

ENABLED_FLAGS = {"new_api"}


def require_feature_flag(flag_name):
    def decorator(func):
        @wraps(func)
        def wrapper(request, *args, **kwargs):
            if flag_name not in ENABLED_FLAGS:
                return 403, {"error": f"Feature '{flag_name}' is not enabled"}
            return func(request, *args, **kwargs)

        return wrapper

    return decorator


router.add_decorator(require_feature_flag("new_api"))


@router.get("/new-feature")
def new_feature(request):
    return {"feature": "enabled"}
```

**Response caching** (VIEW mode) — `func` here is Ninja's whole request
handler, so it takes the raw `HttpRequest` and must return an `HttpResponse`,
same as `func` in the [VIEW vs OPERATION mode](#view-vs-operation-mode) table:

```python
import hashlib
from functools import wraps

from django.core.cache import cache
from ninja import Router

router = Router()


def cache_response(timeout=300):
    def decorator(func):
        @wraps(func)
        def wrapper(request, *args, **kwargs):
            cache_key = hashlib.md5(
                f"{request.path}{request.GET.urlencode()}".encode()
            ).hexdigest()
            response = cache.get(cache_key)
            if response is None:
                response = func(request, *args, **kwargs)
                cache.set(cache_key, response, timeout)
            return response

        return wrapper

    return decorator


router.add_decorator(cache_response(600), mode="view")
```

## Decorator order

Operations can pick up decorators from several places at once: their own
`@decorate_view`, the router they're defined on, any routers that router is mounted
under, and the `NinjaAPI` itself. They combine like nested wrapping — whichever one
gets applied last ends up outermost, so it's the first to run and the last to
finish.

Ninja applies them API-level first, then parent routers, then the more specific
child routers — so **the most specific router's decorators end up outermost**, and
API-level decorators end up right next to whatever they're wrapping:

```python hl_lines="21 22 23"
from ninja import NinjaAPI, Router

order = []


def track(name):
    def decorator(func):
        def wrapper(request, *args, **kwargs):
            order.append(name)
            return func(request, *args, **kwargs)

        return wrapper

    return decorator


api = NinjaAPI()
parent_router = Router()
child_router = Router()

api.add_decorator(track("api"))
parent_router.add_decorator(track("parent"))
child_router.add_decorator(track("child"))


@child_router.get("/ping")
def ping(request):
    return {"order": order}


parent_router.add_router("/child", child_router)
api.add_router("/parent", parent_router)
# GET /parent/child/ping -> {"order": ["child", "parent", "api"]}
```

Putting everything together, here is the full order a request goes through, from
first to last:

1. The most specific router's VIEW-mode decorators
2. Its parent routers' VIEW-mode decorators, outer to inner
3. API-level VIEW-mode decorators
4. The operation's own `@decorate_view` decorators
5. *Ninja runs authentication and throttling checks*
6. *Ninja parses and validates the request parameters*
7. The most specific router's OPERATION-mode decorators
8. Its parent routers' OPERATION-mode decorators, outer to inner
9. API-level OPERATION-mode decorators
10. Your endpoint function
11. *Ninja serializes the return value into a response*

Note that `@decorate_view` ends up innermost among VIEW-mode decorators — it runs
right before Ninja starts validating the request, closer to your function than any
router- or API-level VIEW decorator.

## Async support

Decorators apply the same way to `async def` operations (see
[Async Support](async.md) for the basics of declaring them) — but a plain sync
decorator that calls an async function gets back a coroutine, not the final result,
so it can't just inspect or modify the return value directly.

If a router mixes sync and async endpoints and you want one decorator that works on
both, branch on `asyncio.iscoroutinefunction()` at decoration time:

```python
import asyncio
from functools import wraps

from ninja import Router

router = Router()


def universal_decorator(func):
    if asyncio.iscoroutinefunction(func):

        @wraps(func)
        async def async_wrapper(request, *args, **kwargs):
            result = await func(request, *args, **kwargs)
            if isinstance(result, dict):
                result["decorated"] = True
            return result

        return async_wrapper

    @wraps(func)
    def sync_wrapper(request, *args, **kwargs):
        result = func(request, *args, **kwargs)
        if isinstance(result, dict):
            result["decorated"] = True
        return result

    return sync_wrapper


router.add_decorator(universal_decorator)


@router.get("/async")
async def async_endpoint(request):
    await asyncio.sleep(0)
    return {"endpoint": "async"}


@router.get("/sync")
def sync_endpoint(request):
    return {"endpoint": "sync"}
```

If every endpoint on a router is `async def`, a plain `async def` decorator is
simpler — no branching needed, since there's nothing sync to support:

```python
import asyncio
import time
from functools import wraps

from ninja import Router

router = Router()


def async_timing_decorator(func):
    @wraps(func)
    async def wrapper(request, *args, **kwargs):
        start = time.time()
        result = await func(request, *args, **kwargs)
        if isinstance(result, dict):
            result["_timing"] = f"{time.time() - start:.3f}s"
        return result

    return wrapper


router.add_decorator(async_timing_decorator)


@router.get("/async")
async def async_endpoint(request):
    await asyncio.sleep(1)
    return {"message": "async done"}
```

A third option skips the `iscoroutinefunction` branch entirely: call `func`
unconditionally and inspect what comes back. Calling an `async def` function
returns a coroutine immediately without running any of its code, so
`asyncio.iscoroutine(result)` tells you which case you're in, and you can hand
back an inner `async def` wrapper only when one is needed:

```python
import asyncio
from functools import wraps


def sync_decorator(func):
    @wraps(func)
    def wrapper(request, *args, **kwargs):
        result = func(request, *args, **kwargs)

        if asyncio.iscoroutine(result):

            async def async_wrapper():
                actual_result = await result
                if isinstance(actual_result, dict):
                    actual_result["sync_decorated"] = True
                return actual_result

            return async_wrapper()

        if isinstance(result, dict):
            result["sync_decorated"] = True
        return result

    return wrapper
```

`wrapper` itself stays a plain sync function — it just returns an awaitable
when it wraps an async endpoint, and a plain value when it wraps a sync one,
so it works as a single `add_decorator()` on a mixed router without the
`iscoroutinefunction` branch above.

## Tips

!!! tip "Use `functools.wraps`"
    Always wrap your inner function with `@wraps(func)`. Beyond preserving the
    original name and docstring, Ninja specifically checks for this: if an
    OPERATION-mode decorator swallows `**kwargs` without `@wraps`, the resulting
    `TypeError` comes back with the hint *"Did you fail to use functools.wraps() in
    a decorator?"* attached.

!!! note "Reusing the same router"
    If you mount the same `Router` instance more than once — under two different
    `NinjaAPI` instances, or twice in the same one — each mount gets its own cloned
    copy of the operations. Decorators are applied fresh to each copy, so they never
    stack up or leak between mounts.
