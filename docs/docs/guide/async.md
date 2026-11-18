# Async Support

Django has supported async views since **version 3.1**, and Django Ninja takes full
advantage of them. Async views pay off when an operation is network- or IO-bound —
calling external APIs, waiting on database queries, or reading/writing files — since a
single worker can hold many requests in flight instead of blocking a thread on each one.
For the basics of declaring `async def` operations, see [Operations](operations.md#sync-vs-async).
This page covers what's specific to running async code: serving it, mixing it with sync
code, and using it safely with the Django ORM.

## Quick example

Here's a plain sync operation that sleeps for a while and returns a word:

```python
import time

from ninja import NinjaAPI

api = NinjaAPI()


@api.get("/say-after")
def say_after(request, delay: int, word: str):
    time.sleep(delay)
    return {"saying": word}
```

Turning it into an async operation just means adding `async` to the function and
using an async-aware library for the actual work — here, swapping the stdlib `time.sleep`
for `asyncio.sleep`:

```python hl_lines="1 9 10"
import asyncio

from ninja import NinjaAPI

api = NinjaAPI()


@api.get("/say-after")
async def say_after(request, delay: int, word: str):
    await asyncio.sleep(delay)
    return {"saying": word}
```

## Running under ASGI

To actually get the concurrency benefit, serve the project with an ASGI server such as
<a href="https://www.uvicorn.dev/" target="_blank">Uvicorn</a> or
<a href="https://github.com/django/daphne" target="_blank">Daphne</a>:

```
pip install uvicorn
uvicorn your_project.asgi:application --reload
```

Replace `your_project` with your project's package name (the one containing `asgi.py`).
Don't use `--reload` in production.

!!! note
    `manage.py runserver` can run async views too, but it doesn't behave well with every
    async library. Prefer a real ASGI server such as Uvicorn or Daphne, including for local
    testing of anything performance-sensitive.

### Seeing the concurrency

With the server above running, flood the async `/say-after` operation with 100 concurrent
requests using <a href="https://httpd.apache.org/docs/2.4/programs/ab.html" target="_blank">`ab`</a>:

```
ab -c 100 -n 100 "http://127.0.0.1:8000/api/say-after?delay=3&word=hello"
```

Even though each request sleeps for 3 seconds and there are 100 of them in flight at
once, they all come back in about 3 seconds total — a single worker's event loop holds
all 100 `asyncio.sleep` calls concurrently instead of blocking a thread on each one:

```
Percentage of the requests served within a certain time (ms)
  50%   3070
  95%   3082
 100%   3083 (longest request)
```

Getting the same concurrency out of the **sync** version above with a WSGI server would
take roughly 10 workers with 10 threads each — 100 OS threads sitting idle in
`time.sleep`, one per in-flight request.

## Mixing sync and async operations

Sync and async operations can live side by side in the same `NinjaAPI` or `Router` —
Django Ninja routes each one correctly without any extra configuration:

```python hl_lines="10 16"
import asyncio
import time

from ninja import NinjaAPI

api = NinjaAPI()


@api.get("/say-sync")
def say_after_sync(request, delay: int, word: str):
    time.sleep(delay)
    return {"saying": word}


@api.get("/say-async")
async def say_after_async(request, delay: int, word: str):
    await asyncio.sleep(delay)
    return {"saying": word}
```

!!! tip
    If two operations share the exact same **path** (e.g. a `GET` and a `POST` on
    `/items/{id}`) and only one of them is `async def`, Django Ninja still serves both
    correctly — the sync one is transparently wrapped so the whole path can be handled
    as async. You don't need to make every operation on a path async just because one of
    them is.

## A real-world example: Elasticsearch

Libraries that ship an async client need no extra plumbing to work with async
operations. For example, the
<a href="https://elasticsearch-py.readthedocs.io/" target="_blank">`elasticsearch`</a>
package (7.8+) ships an `AsyncElasticsearch` client alongside its sync one:

```
pip install "elasticsearch>=7.8.0"
```

Use it exactly like the sync client, just `await` the calls:

```python hl_lines="2 6 11"
from ninja import NinjaAPI
from elasticsearch import AsyncElasticsearch

api = NinjaAPI()

es = AsyncElasticsearch()


@api.get("/search")
async def search(request, q: str):
    resp = await es.search(
        index="documents",
        query={"query_string": {"query": q}},
        size=20,
    )
    return resp["hits"]
```

## Using the Django ORM from async code

The ORM is **async-unsafe**: it has global state that isn't coroutine-aware, and Django
raises an error if you touch it directly from inside an `async def` view. Read more in
the <a href="https://docs.djangoproject.com/en/stable/topics/async/#async-safety" target="_blank">Django async safety docs</a>.

So this raises an error:

```python hl_lines="3"
@api.get("/blog/{post_id}")
async def get_blog(request, post_id: int):
    blog = Blog.objects.get(pk=post_id)
    ...
```

### Async ORM methods (Django 4.1+)

Since Django 4.1, most queryset methods have an async counterpart with the same name
prefixed with `a` — `aget`, `acreate`, `aupdate`, `adelete`, `aget_or_create`, and so on.
Prefer these over `sync_to_async` where they're available:

```python hl_lines="3"
@api.get("/blog/{post_id}")
async def get_blog(request, post_id: int):
    blog = await Blog.objects.aget(pk=post_id)
    ...
```

To iterate a queryset, use `async for`:

```python hl_lines="3"
@api.get("/blogs")
async def list_blogs(request):
    return [blog async for blog in Blog.objects.values()]
```

See the <a href="https://docs.djangoproject.com/en/stable/topics/async/#asynchronous-support" target="_blank">Django async ORM docs</a> for the full list of `a`-prefixed methods.

### `sync_to_async` fallback

For anything without an async counterpart (a custom manager method, a third-party
library that assumes sync Django, etc.), wrap it with
<a href="https://docs.djangoproject.com/en/stable/topics/async/#asgiref.sync.sync_to_async" target="_blank">`sync_to_async`</a>
from `asgiref`:

```python hl_lines="1 4 11"
from asgiref.sync import sync_to_async


@sync_to_async
def get_blog(post_id):
    return Blog.objects.get(pk=post_id)


@api.get("/blog/{post_id}")
async def get_blog_view(request, post_id: int):
    blog = await get_blog(post_id)
    ...
```

or inline, without a wrapper function:

```python hl_lines="3"
@api.get("/blog/{post_id}")
async def get_blog_view(request, post_id: int):
    blog = await sync_to_async(Blog.objects.get)(pk=post_id)
    ...
```

!!! warning "Querysets are lazy"
    A queryset itself isn't evaluated until you iterate it, so wrapping the queryset
    expression doesn't help — the actual database hit happens later, outside the wrapper,
    and raises the async-unsafe error anyway:

    ```python
    all_blogs = await sync_to_async(Blog.objects.all)()
    # fails later, when something iterates over all_blogs
    ```

    Force evaluation *inside* the wrapped call instead, e.g. with `list`:

    ```python
    all_blogs = await sync_to_async(list)(Blog.objects.all())
    ```

    Or use `async for` / the `a`-prefixed methods above, which don't have this problem.

## Async support elsewhere in Django Ninja

Async operations are supported throughout the framework, not just for the view body
itself:

- **Authentication** — an auth class's `authenticate()` (or a plain function passed to
  `auth=`) can be `async def`; Django Ninja awaits it correctly regardless of whether the
  operation itself is sync or async. See [Async authentication](authentication.md#async-authentication).
- **Pagination** — all built-in pagination classes work transparently with `async def`
  operations, and a custom paginator can subclass `AsyncPaginationBase` to support them
  too. See [Pagination: async support](pagination.md#async-support).
- **Testing** — `ninja.testing` provides `TestAsyncClient` alongside the sync
  `TestClient`, for exercising async operations with `await client.get(...)` in your
  tests without running a real ASGI server. See [Testing](testing.md).
