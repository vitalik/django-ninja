# Throttling

Throttling controls the rate of requests that a client can make to your API. Like [authentication](authentication.md), a throttle can be set globally (on the `NinjaAPI` instance), on a router, or on an individual operation — and Django Ninja's design is modelled closely on [DRF's throttling](https://www.django-rest-framework.org/api-guide/throttling/), so existing knowledge (and often existing custom throttles) transfers directly. The one difference is that you pass **initialized throttle objects**, not classes.

!!! warning
    Application-level throttling is not a security measure and shouldn't be relied on to prevent brute-forcing or denial-of-service attacks — a determined attacker can always spoof the request's origin. The built-in throttles are implemented on top of Django's cache framework using non-atomic operations, so the enforced rate can be slightly fuzzy under concurrent load.

## Basic usage

Pass one throttle, or a list of throttles, to `throttle=`. Each throttle checks the request independently; if any of them rejects the request, a `429 Too Many Requests` response is returned.

```python
from ninja import NinjaAPI
from ninja.throttling import AnonRateThrottle, AuthRateThrottle

api = NinjaAPI(
    throttle=[
        AnonRateThrottle("10/s"),
        AuthRateThrottle("100/s"),
    ],
)
```

This limits unauthenticated clients to 10 requests per second, while authenticated clients get 100/s.

### Rate format

A rate is a string in the form `"<requests>/<period>"`. The period is a number followed by a unit, and both are optional: an omitted number defaults to `1`, and an omitted unit defaults to seconds. These are all equivalent, and all mean "100 requests per 5 minutes":

```python
"100/5m"
"100/300s"
"100/300"
```

Supported units:

- `s` or `sec` — seconds
- `m` or `min` — minutes
- `h` or `hour` — hours
- `d` or `day` — days

## Router and operation level

A throttle set on a router or operation overrides (does not add to) whatever was set above it — the most specific `throttle=` wins.

Pass `throttle` to `Router()`:

```python
from ninja import Router
from ninja.throttling import AnonRateThrottle

router = Router(throttle=[AnonRateThrottle("1000/h")])
```

or to `api.add_router()`, to override it just for that mount:

```python
api.add_router("/sensitive", "myapp.api.router", throttle=AnonRateThrottle("100/m"))
```

And on an individual operation, which overrules both the API-level and router-level throttles:

```python
from ninja.throttling import UserRateThrottle


@api.get("/some", throttle=[UserRateThrottle("10000/d")])
def some(request):
    ...
```

## Built-in throttles

All built-in throttles live in `ninja.throttling` and key their cache entry on some identifier extracted from the request.

### AnonRateThrottle

Throttles unauthenticated requests only (`request.auth is None`); authenticated requests are never limited by it. The client's IP address is the cache key.

### UserRateThrottle

Throttles by Django's built-in user (`request.user`). If the user is authenticated, `request.user.pk` is the cache key; otherwise it falls back to the client's IP address.

### AuthRateThrottle

Throttles by Django Ninja's own [`request.auth`](authentication.md) instead of `request.user`, so it works with any auth scheme (API keys, custom auth classes, etc.), not just Django's session/user auth. If unauthenticated, it falls back to the IP address.

!!! note
    The cache key for an authenticated request is `sha256(str(request.auth))`. If your authentication class resolves to a custom object, implement `__str__` on it so it returns something unique per user — otherwise every authenticated user could share the same throttle bucket.

### Default rates per scope

Each built-in throttle has a `scope` (`"anon"`, `"user"` or `"auth"`). If you instantiate one **without** a rate, it looks its rate up from `NINJA_DEFAULT_THROTTLE_RATES` instead:

```python
from ninja.throttling import AnonRateThrottle

AnonRateThrottle()  # uses NINJA_DEFAULT_THROTTLE_RATES["anon"]
```

```python
# settings.py
NINJA_DEFAULT_THROTTLE_RATES = {
    "auth": "10000/day",
    "user": "10000/day",
    "anon": "1000/day",
}
```

These are the built-in defaults, so `AnonRateThrottle()`, `UserRateThrottle()` and `AuthRateThrottle()` all work out of the box without passing a rate — override the settings dict to change them project-wide.

### Client IP and `NINJA_NUM_PROXIES`

`AnonRateThrottle` and the "fall back to IP" branches of the other throttles use `get_ident()`, which reads `HTTP_X_FORWARDED_FOR` / `REMOTE_ADDR`. If your API sits behind a known number of trusted reverse proxies, set `NINJA_NUM_PROXIES` so the real client IP is extracted from `X-Forwarded-For` correctly instead of picking up a proxy's address:

```python
# settings.py
NINJA_NUM_PROXIES = 1
```

With `NINJA_NUM_PROXIES` unset (the default), the entire `X-Forwarded-For` header (whitespace stripped) is used as the identifier.

## Custom throttles

Subclass `BaseThrottle` (or any built-in throttle) and implement `allow_request(self, request)`, returning `True` to allow the request and `False` to throttle it:

```python
from ninja.throttling import AnonRateThrottle


class NoReadsThrottle(AnonRateThrottle):
    """Never throttle GET requests."""

    def allow_request(self, request):
        if request.method == "GET":
            return True
        return super().allow_request(request)
```

For a fully custom rate-limiting strategy, subclass `SimpleRateThrottle` and override `get_cache_key()` — it returns the cache key to bucket the request under, or `None` to skip throttling for that request entirely:

```python
from ninja.throttling import SimpleRateThrottle


class BurstRateThrottle(SimpleRateThrottle):
    scope = "burst"

    def get_cache_key(self, request):
        ident = self.get_ident(request)
        return self.cache_format % {"scope": self.scope, "ident": ident}
```

`SimpleRateThrottle` also exposes a few class attributes you can override: `cache` (defaults to Django's default cache), `cache_format` (defaults to `"throttle_%(scope)s_%(ident)s"`), and `THROTTLE_RATES` (defaults to `NINJA_DEFAULT_THROTTLE_RATES`).

## Response format

When a request is throttled, Django Ninja returns `429 Too Many Requests` with:

```json
{"detail": "Too many requests."}
```

If a throttle's `wait()` method returns a number of seconds until the next allowed request, it's rounded up and added as a `Retry-After` header. When multiple throttles reject the same request, the longest wait time is used. Like any exception, this is customizable via [exception handlers](errors.md) — register a handler for `ninja.errors.Throttled` to change the response body or status code.
