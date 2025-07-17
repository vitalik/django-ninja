## Intro

Since **version 3.1**, Django comes with **async views support**. This allows you run efficient concurrent views that are network and/or IO bound.

```
pip install Django>=3.1 django-ninja
```

Async views work more efficiently when it comes to:

- calling external APIs over the network
- executing/waiting for database queries
- reading/writing from/to disk drives

**Django Ninja** takes full advantage of async views and makes it very easy to work with them.

## Quick example

### Code

Let's take an example.  We have an API operation that does some work (currently just sleeps for provided number of seconds) and returns a word:

```python hl_lines="5"
import time

@api.get("/say-after")
def say_after(request, delay: int, word: str):
    time.sleep(delay)
    return {"saying": word}
```

To make this code asynchronous, all you have to do is add the **`async`** keyword to a function (and use async aware libraries for work processing - in our case we will replace the stdlib `sleep` with `asyncio.sleep`):

```python hl_lines="1 4 5"
import asyncio

@api.get("/say-after")
async def say_after(request, delay: int, word: str):
    await asyncio.sleep(delay)
    return {"saying": word}
```

### Run

To run this code you need an ASGI server like <a href="https://www.uvicorn.org/" target="_blank">Uvicorn</a> or <a href="https://github.com/django/daphne" target="_blank">Daphne</a>. Let's use Uvicorn for, example:

To install Uvicorn, use:

```
pip install uvicorn
```

Then start the server:

```
uvicorn your_project.asgi:application --reload
```

> <small>
> *Note: replace `your_project` with your project package name*<br>
> *`--reload` flag used to automatically reload server if you do any changes to the code (do not use on production)*
> </small>

!!! note
    You can run async views with `manage.py runserver`, but it does not work well with some libraries, so at this time (July 2020) it is recommended to use ASGI servers like Uvicorn or Daphne.

### Test

Go to your browser and open <a href="http://127.0.0.1:8000/api/say-after?delay=3&word=hello" target="_blank">http://127.0.0.1:8000/api/say-after?delay=3&word=hello</a> (**delay=3**)
After a 3-second wait you should see the "hello" message.

Now let's flood this operation with **100 parallel requests**:

```
ab -c 100 -n 100 "http://127.0.0.1:8000/api/say-after?delay=3&word=hello"
```

which will result in something like this:

```
Connection Times (ms)
              min  mean[+/-sd] median   max
Connect:        0    1   1.1      1       4
Processing:  3008 3063  16.2   3069    3082
Waiting:     3008 3062  15.7   3068    3079
Total:       3008 3065  16.3   3070    3083

Percentage of the requests served within a certain time (ms)
  50%   3070
  66%   3072
  75%   3075
  80%   3076
  90%   3081
  95%   3082
  98%   3083
  99%   3083
 100%   3083 (longest request)
```

Based on the numbers, our service was able to handle each of the 100 concurrent requests with just a little overhead.

To achieve the same concurrency with WSGI and sync operations you would need to spin up about 10 workers with 10 threads each!

## Mixing sync and async operations

Keep in mind that you can use **both sync and async operations** in your project, and **Django Ninja** will route it automatically:

```python hl_lines="2 7"

@api.get("/say-sync")
def say_after_sync(request, delay: int, word: str):
    time.sleep(delay)
    return {"saying": word}

@api.get("/say-async")
async def say_after_async(request, delay: int, word: str):
    await asyncio.sleep(delay)
    return {"saying": word}
```

## Elasticsearch example

Let's take a real world use case. For this example, let's use the latest version of Elasticsearch that now comes with async support:

```
pip install elasticsearch>=7.8.0
```

And now instead of the `Elasticsearch` class, use the `AsyncElasticsearch` class and `await` the results:

```python hl_lines="2 7 11 12"
from ninja import NinjaAPI
from elasticsearch import AsyncElasticsearch


api = NinjaAPI()

es = AsyncElasticsearch()


@api.get("/search")
async def search(request, q: str):
    resp = await es.search(
        index="documents", 
        body={"query": {"query_string": {"query": q}}},
        size=20,
    )
    return resp["hits"]
```

## Using ORM

Currently, certain key parts of Django are not able to operate safely in an async environment, as they have global state that is not coroutine-aware. These parts of Django are classified as “async-unsafe”, and are protected from execution in an async environment. **The ORM** is the main example, but there are other parts that are also protected in this way.

Learn more about async safety here in the <a href="https://docs.djangoproject.com/en/stable/topics/async/#async-safety" target="_blank">official Django docs</a>.

So, if you do this:

```python hl_lines="3"
@api.get("/blog/{post_id}")
async def search(request, post_id: int):
    blog = Blog.objects.get(pk=post_id)
    ...
```

it throws an error. Until the async ORM is implemented, you can use the `sync_to_async()` adapter:

```python hl_lines="1 3 9"
from asgiref.sync import sync_to_async

@sync_to_async
def get_blog(post_id):
    return Blog.objects.get(pk=post_id)

@api.get("/blog/{post_id}")
async def search(request, post_id: int):
    blog = await get_blog(post_id)
    ...
```

or even shorter:

```python hl_lines="3"
@api.get("/blog/{post_id}")
async def search(request, post_id: int):
    blog = await sync_to_async(Blog.objects.get)(pk=post_id)
    ...
```

There is a common **GOTCHA**: Django querysets are lazily evaluated (database query happens only when you start iterating), so this will **not** work:

```python
all_blogs = await sync_to_async(Blog.objects.all)()
# it will throw an error later when you try to iterate over all_blogs
...
```

Instead, use evaluation (with `list`):

```python
all_blogs = await sync_to_async(list)(Blog.objects.all())
...
```

Since Django **version 4.1**, Django comes with asynchronous versions of ORM operations.
These eliminate the need to use `sync_to_async` in most cases.
The async operations have the same names as their sync counterparts but are prepended with *a*. So using
the example above, you can rewrite it as:

```python hl_lines="3"
@api.get("/blog/{post_id}")
async def search(request, post_id: int):
    blog = await Blog.objects.aget(pk=post_id)
    ...
```

When working with querysets, use `async for` paired with list comprehension:

```python
all_blogs = [blog async for blog in Blog.objects.all()]
...
```

Learn more about the async ORM interface in the <a href="https://docs.djangoproject.com/en/4.1/releases/4.1/#asynchronous-orm-interface" target="_blank">official Django docs</a>.
