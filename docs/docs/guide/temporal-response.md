# Headers, Cookies & Temporal Response

To read a header or cookie from the *request*, see [Headers &
Cookies](headers-cookies.md). This page covers the other direction: setting a
header, cookie or status code on the *response*, from inside your view.

## The `response` argument

Declare a function parameter annotated with Django's `HttpResponse` and
**Django Ninja** passes you a response object to modify. Anything you set on
it — headers, cookies — ends up on the response that's actually sent:

```python hl_lines="8 9 10"
from django.http import HttpResponse
from ninja import NinjaAPI

api = NinjaAPI()


@api.get("/cookie")
def feed_cookiemonster(request, response: HttpResponse):
    response.set_cookie("cookie", "delicious")
    response["X-Cookiemonster"] = "blue"
    return {"cookiemonster_happy": True}
```

You still return your normal data (a `dict`, a `Schema`, a list, ...) — the
`response` object is for headers, cookies and status, not for the body.

The argument is matched **by type, not by name** — call it `response`,
`res`, `resp`, whatever reads best. It also works the same way in `async def`
views.

## Setting headers

Assign to the response like a `dict`:

```python hl_lines="2 3"
def my_view(request, response: HttpResponse):
    response["X-Total-Count"] = 42
    response["Cache-Control"] = "no-cache"
    return {"ok": True}
```

## Setting cookies

Use Django's `HttpResponse.set_cookie()` / `delete_cookie()` — **Django
Ninja** doesn't wrap these, so every argument Django supports is available:
`max_age`, `expires`, `path`, `domain`, `secure`, `httponly`, `samesite`:

```python hl_lines="2-9 14"
def login(request, response: HttpResponse):
    response.set_cookie(
        "session_id",
        "abc123",
        max_age=3600,
        secure=True,
        httponly=True,
        samesite="Lax",
    )
    return {"logged_in": True}


def logout(request, response: HttpResponse):
    response.delete_cookie("session_id")
    return {"logged_in": False}
```

## Setting the status code

You can set `response.status_code` directly, but it only sticks if your view
also returns something that leaves the status computation alone — which
means a plain dict/`Schema`/list is **not** enough by itself:

```python hl_lines="3"
@api.get("/broken")
def broken(request, response: HttpResponse):
    response.status_code = 201  # gets overwritten back to 200 below
    return {"created": True}
```

**Django Ninja** works out the status code from your *return value* — 200 by
default, unless you declare and return a [`Status`](responses.md) object —
and writes it onto the response *after* your view returns, unconditionally
overwriting anything you assigned manually. To set a non-default status
alongside a body, return a `Status`:

```python hl_lines="1 6 9"
from ninja import NinjaAPI, Status

api = NinjaAPI()


@api.post("/items", response={200: dict, 201: dict})
def create_item(request, response: HttpResponse):
    response["Location"] = "/items/1"
    return Status(201, {"id": 1, "created": True})
```

Headers and cookies you set on `response` are preserved either way — only
`status_code` is at risk of being overwritten.

!!! tip
    Returning the `response` object itself (after setting `.status_code`,
    `.content`, headers, cookies, ...) always works, since **Django Ninja**
    returns any `HttpResponse` you give it as-is. See
    [Responses](responses.md) for the full return-value protocol.

## The temporal response object

The object you receive is created fresh for every request, before your view
runs, by `NinjaAPI.create_temporal_response()`. At that point it has no
content yet — only a `Content-Type` matching the configured
[renderer](renderers.md). After your view returns, **Django Ninja** copies
its headers, cookies and (computed) status code onto the final response.

!!! warning
    This only applies to responses your *operation* builds. Built-in error
    responses — a `404`, a validation `422`, an `HttpError`, or the default
    exception handler — are built independently and don't inherit headers or
    cookies you set on `response` before the exception was raised. Set those
    headers in a custom [exception handler](errors.md) instead if you need
    them on error responses too.

## Customizing the base response

Override `create_temporal_response()` on a `NinjaAPI` subclass to change what
every response starts out as — for example to add a header to every
response from this API:

```python hl_lines="6-9"
from django.http import HttpRequest, HttpResponse
from ninja import NinjaAPI


class MyAPI(NinjaAPI):
    def create_temporal_response(self, request: HttpRequest) -> HttpResponse:
        response = super().create_temporal_response(request)
        response["X-Powered-By"] = "Django Ninja"
        return response


api = MyAPI()
```
