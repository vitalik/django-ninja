# Testing

**Django Ninja** works with Django's regular [test client](https://docs.djangoproject.com/en/stable/topics/testing/tools/)
out of the box, since every operation is still a normal Django view. It also ships a
lightweight `TestClient` (and an async counterpart, `TestAsyncClient`) built specifically
for APIs: instead of going through URL resolution and the full middleware stack, it calls
the matching operation function directly, so tests run faster and a `Router` can be
exercised entirely on its own, without ever attaching it to a `NinjaAPI`.

## Basic usage

```python hl_lines="2 16 20-22"
from ninja import NinjaAPI, Schema
from ninja.testing import TestClient

api = NinjaAPI()


class HelloResponse(Schema):
    msg: str


@api.get("/hello", response=HelloResponse)
def hello(request):
    return {"msg": "Hello World"}


client = TestClient(api)


def test_hello():
    response = client.get("/hello")
    assert response.status_code == 200
    assert response.json() == {"msg": "Hello World"}
```

`TestClient` accepts either a full `NinjaAPI` instance or a bare `Router`. `get`, `post`,
`put`, `patch` and `delete` all take the path first, then whatever the request needs — see
below.

### Without pytest

`TestClient` doesn't care how it's called, so it works just as well from a Django
`TestCase` and `self.assertEqual` as it does from a bare `assert`:

```python hl_lines="1 20-24"
from django.test import TestCase
from ninja import NinjaAPI, Schema
from ninja.testing import TestClient

api = NinjaAPI()


class HelloResponse(Schema):
    msg: str


@api.get("/hello", response=HelloResponse)
def hello(request):
    return {"msg": "Hello World"}


client = TestClient(api)


class HelloTest(TestCase):
    def test_hello(self):
        response = client.get("/hello")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {"msg": "Hello World"})
```

## Testing a router in isolation

Pass a `Router` straight to `TestClient` and it builds a throwaway `NinjaAPI` behind the
scenes to resolve URLs against, without touching the router you pass in — handy for
testing one router's operations without wiring up the rest of the API:

```python hl_lines="16"
from ninja import Router, Schema
from ninja.testing import TestClient

router = Router()


class HelloResponse(Schema):
    msg: str


@router.get("/hello", response=HelloResponse)
def hello(request):
    return {"msg": "Hello World"}


client = TestClient(router)


def test_hello():
    response = client.get("/hello")
    assert response.json() == {"msg": "Hello World"}
```

## Sending data

### JSON body

Pass `json=` — a `dict` or a `Schema` instance — and it's serialized and sent as the
request body, exactly like a real client's `Content-Type: application/json` request:

```python hl_lines="20"
from ninja import NinjaAPI, Schema
from ninja.testing import TestClient

api = NinjaAPI()


class Payload(Schema):
    name: str


@api.post("/echo")
def echo(request, payload: Payload):
    return {"name": payload.name}


client = TestClient(api)


def test_echo():
    response = client.post("/echo", json={"name": "Ninja"})
    assert response.json() == {"name": "Ninja"}
```

### Form data

Pass `data=` for a `application/x-www-form-urlencoded`-style body instead — a plain
`dict` is turned into the request's `POST` `QueryDict`:

```python
response = client.post("/items", data={"name": "Katana", "qty": 3})
```

### Query parameters

Either put the query string directly in `path`, or pass a `dict` as `query_params=` (only
used when `path` has no `?` of its own). A `list` value sends the same key multiple
times:

```python
response = client.get("/items?category=tools&category=outdoor")
# same as:
response = client.get("/items", query_params={"category": ["tools", "outdoor"]})
```

## The response object

Every call returns a `NinjaResponse` wrapping the operation's return value:

- `status_code` — the HTTP status code.
- `json()` — the response body, decoded from JSON.
- `data` — a shortcut for `json()`.
- `content` — the raw response bytes (for a streaming response, the streamed chunks
  already joined together).
- `response["Header-Name"]` — read a response header, the same way you'd index a Django
  `HttpResponse`.

```python
response = client.get("/hello")
assert response.status_code == 200
assert response.data == {"msg": "Hello World"}
assert response["Content-Type"] == "application/json; charset=utf-8"
```

## Headers and cookies

Pass `headers=`/`COOKIES=` when constructing `TestClient` for values every request should
carry, and again per request to add to or override them for that one call:

```python
client = TestClient(router, headers={"A": "a", "B": "b"}, COOKIES={"A": "a"})

# request headers end up {"A": "na", "B": "b", "C": "nc"}
response = client.get("/test-headers", headers={"A": "na", "C": "nc"})

# request cookies end up {"A": "na"}
response = client.get("/test-cookies", COOKIES={"A": "na"})
```

## Testing authenticated views

By default `request.user` is an unauthenticated mock (`is_authenticated`, `is_staff` and
`is_superuser` all `False`), so an operation behind [`auth=django_auth`](authentication.md)
gets rejected. Pass `user=` to set `request.user` to a real user instead:

```python hl_lines="19"
from django.contrib.auth.models import User
from ninja import NinjaAPI
from ninja.security import django_auth
from ninja.testing import TestClient

api = NinjaAPI(auth=django_auth)


@api.get("/me")
def me(request):
    return {"username": request.user.username}


client = TestClient(api)


def test_me(db):
    user = User.objects.create(username="ninja")
    response = client.get("/me", user=user)
    assert response.json() == {"username": "ninja"}
```

Auth classes that don't rely on `request.user` — [API key, HTTP Bearer/Basic](authentication.md)
— need no special setup: send the real credentials as a header, query param or cookie,
the same way a live client would.

## Arbitrary request attributes

Any keyword that isn't one of `data`, `json`, `headers`, `COOKIES`, `query_params`,
`FILES`, `META`, `body` or `user` is set directly on the request object — useful for
faking whatever a piece of middleware would normally attach:

```python
# request.company_id is set before the view runs
response = client.get("/hello", company_id=1)
```

## File uploads

Pass `FILES=` — a `dict` of Django `UploadedFile`s (`django.core.files.uploadedfile.SimpleUploadedFile`
is the easiest way to build one in tests). Use a `MultiValueDict` instead of a plain
`dict` to send several files under the same field name (see [File Uploads](files.md)):

```python hl_lines="1 18"
from django.core.files.uploadedfile import SimpleUploadedFile
from ninja import File, NinjaAPI, UploadedFile
from ninja.testing import TestClient

api = NinjaAPI()


@api.post("/upload")
def upload(request, file: UploadedFile = File(...)):
    return {"name": file.name, "data": file.read().decode()}


client = TestClient(api)


def test_upload():
    file = SimpleUploadedFile("test.txt", b"data123")
    response = client.post("/upload", FILES={"file": file})
    assert response.json() == {"name": "test.txt", "data": "data123"}
```

## Testing async operations

Use `TestAsyncClient` for `async def` operations — it has the same `get`/`post`/`put`/`patch`/`delete`
methods, all `await`-able, and it also accepts either a `NinjaAPI` or a `Router`:

```python hl_lines="2 13 16"
import pytest
from ninja.testing import TestAsyncClient
from ninja import NinjaAPI

api = NinjaAPI()


@api.get("/hello")
async def hello(request):
    return {"msg": "Hello World"}


client = TestAsyncClient(api)


@pytest.mark.asyncio
async def test_hello():
    response = await client.get("/hello")
    assert response.status_code == 200
    assert response.json() == {"msg": "Hello World"}
```

!!! note
    `TestAsyncClient` needs an async test runner such as
    [`pytest-asyncio`](https://pytest-asyncio.readthedocs.io/) (`@pytest.mark.asyncio`) —
    it's a dev dependency of Django Ninja itself, so its own test suite uses the same
    pattern.

## Tips

- `TestClient`/`TestAsyncClient` bypass URL resolution and Django's middleware to keep
  tests fast and focused on operation logic. If you need to exercise the full stack —
  real middleware, CSRF enforcement, the URL conf as configured in your project — fall
  back to Django's own `django.test.Client` (or `TestCase.client`); Django Ninja's views
  are ordinary Django views and work with it unmodified.
- Both clients raise a plain `Exception` if `path` doesn't match any operation on the
  router/API being tested — a quick way to catch a typo before it becomes a 404 assertion.
- Anything touching the database needs a DB-enabled test — Django's `TestCase`, or the
  `db`/`transactional_db` fixtures from [`pytest-django`](https://pytest-django.readthedocs.io/),
  as used above in [Testing authenticated views](#testing-authenticated-views).
