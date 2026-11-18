# CSRF

[Cross-Site Request Forgery](https://en.wikipedia.org/wiki/Cross-site_request_forgery)
lets a malicious site trigger a request against your API using a logged-in
user's own browser — relying on credentials the browser attaches
automatically, such as cookies. **Django Ninja** enables CSRF protection
automatically wherever it detects that risk, and leaves it off everywhere
else.

## How it fits together

Every **Django Ninja** view is marked CSRF-exempt at the Django middleware
level — Django's own `CsrfViewMiddleware` never gets a chance to reject a
request. CSRF checking is instead done explicitly, at authentication time, by
any auth class based on `APIKeyCookie` (which includes `django_auth`):

- If the operation has **no auth**, or uses an auth method that isn't
  automatically attached by the browser (an `Authorization` header, an API
  key in the query string, `HttpBasicAuth`, `HttpBearer`, ...), there's
  nothing to check and the request always goes through.
- If the operation authenticates with a **cookie** (`APIKeyCookie`,
  `django_auth`, or your own subclass), the auth class validates the CSRF
  token itself before returning a user, using the same logic as Django's
  middleware — so it recognizes both the `csrfmiddlewaretoken` form field
  and the `X-CSRFToken` header.

```python hl_lines="12"
from django.utils.crypto import constant_time_compare

from ninja import NinjaAPI
from ninja.security import APIKeyCookie


class CookieAuth(APIKeyCookie):
    def authenticate(self, request, key):
        return constant_time_compare(key, "test")


api = NinjaAPI(auth=CookieAuth())
```

A `POST`/`PUT`/`PATCH`/`DELETE` against any operation on this `api` now
requires a valid CSRF token, exactly as it would for a regular Django view.

## Session (`django_auth`) authentication

`django_auth` is just `SessionAuth()`, itself a subclass of `APIKeyCookie` —
so it enables the same CSRF check for free:

```python hl_lines="4"
from ninja import NinjaAPI
from ninja.security import django_auth

api = NinjaAPI(auth=django_auth)
```

## Turning CSRF off for a cookie auth class

`APIKeyCookie` takes a `csrf` argument (default `True`). Pass `csrf=False`
if a particular cookie-based auth class genuinely doesn't need the check —
for example a cookie that only carries an opaque, unguessable API key rather
than a browser session:

```python hl_lines="8"
from django.utils.crypto import constant_time_compare

from ninja.security import APIKeyCookie


class UnprotectedCookieAuth(APIKeyCookie):
    def __init__(self):
        super().__init__(csrf=False)

    def authenticate(self, request, key):
        return constant_time_compare(key, "test")
```

!!! warning
    Only do this if you're sure the cookie can't be used to forge a request
    from another site — disabling the check on `django_auth` or a session
    cookie defeats the purpose of using cookies for auth in the first place.

## Exempting a single operation

Sometimes you need an endpoint that a cookie-authenticated client can reach
without a CSRF token — most commonly, an endpoint whose only job is to hand
out the CSRF cookie in the first place, using Django's
[`ensure_csrf_cookie`](https://docs.djangoproject.com/en/stable/ref/csrf/#django.views.decorators.csrf.ensure_csrf_cookie)
decorator:

```python hl_lines="5-6"
from django.http import HttpResponse
from django.views.decorators.csrf import csrf_exempt, ensure_csrf_cookie

@api.post("/csrf")
@ensure_csrf_cookie
@csrf_exempt
def get_csrf_token(request):
    return HttpResponse()
```

A request to this operation returns a response with a `Set-Cookie` header
carrying the CSRF token, ready for the frontend to read and send back on
later requests. A few things to keep in mind:

- The route decorator (`@api.post(...)`) must be **above** `ensure_csrf_cookie`.
- The operation must also be decorated with Django's `@csrf_exempt` —
  **Django Ninja** reads that flag off the view function and skips its own
  cookie-auth CSRF check for that operation (it doesn't change anything for
  requests without cookie auth, which were never checked).
- `ensure_csrf_cookie` only works on a real Django `HttpResponse` (or a
  subclass, like `JsonResponse`) — not on the dict most **Django Ninja**
  views return.
- If the `NinjaAPI` has a cookie-based auth class set globally (including
  `django_auth`), that auth class still runs for this route and will reject
  the request outright, since it has no CSRF cookie yet — pass `auth=None`
  on the operation to [disable auth](authentication.md) for it specifically.

```python hl_lines="6"
from ninja import NinjaAPI
from ninja.security import django_auth

api = NinjaAPI(auth=django_auth)

@api.post("/csrf", auth=None)
@ensure_csrf_cookie
@csrf_exempt
def get_csrf_token(request):
    return HttpResponse()
```

## Sending the token from the frontend

Once the browser holds the CSRF cookie, read it and attach it to unsafe
requests as either the `X-CSRFToken` header or a `csrfmiddlewaretoken` form
field — see Django's [How to use Django's CSRF
protection](https://docs.djangoproject.com/en/stable/howto/csrf/#using-csrf-protection-with-ajax)
for the exact recipe, `fetch`/`axios` examples included.

!!! tip
    The interactive Swagger docs at `/api/docs` handle this for you: when
    the `NinjaAPI` has an auth class that requires CSRF, **Django Ninja**
    renders the page with the current CSRF token and configures Swagger UI
    to send it as `X-CSRFToken` on every request you try from that page —
    see [OpenAPI & Interactive Docs](openapi.md).

## CORS

None of this is CORS, but the two often show up together: if your frontend
and API live on different origins, the [same-origin
policy](https://developer.mozilla.org/en-US/docs/Web/Security/Same-origin_policy)
blocks the frontend from reading the CSRF cookie set on the API's origin
unless CORS is configured to allow it. See
[django-cors-headers](https://github.com/adamchainz/django-cors-headers) —
Django Ninja has no CORS handling of its own.

## Testing

**Django Ninja**'s [`TestClient`](testing.md) skips CSRF checks by default,
so tests can authenticate with a cookie without generating or attaching a
real token. If you specifically want to test CSRF behavior, build the
request with Django's own test client instead, which does enforce it.
