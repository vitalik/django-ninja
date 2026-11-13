# WebSockets

Django Ninja can serve **WebSocket** endpoints with a syntax close to FastAPI. Nothing extra needs to be installed: the ASGI websocket protocol is implemented directly, so you don't need Django Channels.

```python hl_lines="6"
from ninja import NinjaAPI, WebSocket

api = NinjaAPI()


@api.websocket("/echo")
async def echo(websocket: WebSocket):
    await websocket.accept()
    async for message in websocket.iter_text():
        await websocket.send_text(f"echo: {message}")
```

## Requirements: ASGI

WebSockets only work with an **ASGI** server such as [uvicorn](https://www.uvicorn.org/), [daphne](https://github.com/django/daphne) or [hypercorn](https://hypercorn.readthedocs.io/). WSGI servers (gunicorn sync workers, `mod_wsgi`, `manage.py runserver` without daphne) can't handle them.

Django's own ASGI handler only speaks HTTP, so in `asgi.py` replace `django.core.asgi.get_asgi_application` with the one from `ninja.asgi`:

```python title="asgi.py" hl_lines="3 6"
import os

from ninja.asgi import get_asgi_application

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "mysite.settings")
application = get_asgi_application()
```

HTTP requests still go to Django as before. WebSocket connections are resolved against your `urls.py`, where websocket routes are added through `api.urls` like any other operation:

```python title="urls.py"
urlpatterns = [
    path("api/", api.urls),  # also serves ws://.../api/echo
]
```

Then run your project with an ASGI server:

```
uvicorn mysite.asgi:application --reload
```

!!! note "What if the project runs under WSGI?"
    The websocket path still exists as an HTTP URL. A plain HTTP request returns **426 Upgrade Required**. If an upgrade request reaches Django's HTTP stack (for example a WSGI server), the response explains that an ASGI server and `ninja.asgi` are required. You can also use `reverse()` on websocket routes by their url name.

## The `WebSocket` object

The handler must be an `async def` with a parameter annotated as `WebSocket` (any name works):

| Method | Description |
| --- | --- |
| `await websocket.accept(subprotocol=None, headers=None)` | Accept the connection |
| `await websocket.receive_text()` / `receive_bytes()` | Receive a message |
| `await websocket.receive_json(mode="text", schema=None)` | Receive and decode JSON, optionally validated with a schema |
| `await websocket.send_text(data)` / `send_bytes(data)` | Send a message |
| `await websocket.send_json(data, mode="text", schema=None)` | Send JSON (pydantic models are serialized automatically) |
| `websocket.iter_text()` / `iter_bytes()` / `iter_json()` | Async iterators that stop when the client disconnects |
| `await websocket.close(code=1000, reason=None)` | Close the connection |
| `websocket.query_params`, `headers`, `cookies`, `path_params`, `client`, `subprotocols` | Handshake information |
| `websocket.auth` | The result of the authentication callback |
| `websocket.request` | A read-only Django `HttpRequest` built from the handshake |

When the client disconnects, `receive_*` raises `WebSocketDisconnect`:

```python
from ninja import WebSocket, WebSocketDisconnect


@api.websocket("/chat")
async def chat(websocket: WebSocket):
    await websocket.accept()
    try:
        while True:
            data = await websocket.receive_json()
            await websocket.send_json({"you said": data})
    except WebSocketDisconnect as e:
        print("client left with code", e.code)
```

If the handler returns while the connection is still open, it is closed with code `1000`. If the handler raises an exception, the error is logged (logger `ninja.websockets`) and the connection is closed with code `1011`.

## Path, Query, Header and Cookie parameters

Parameters are read from the handshake exactly like in HTTP operations, and they are validated:

```python
from ninja import Header, Query


@api.websocket("/rooms/{room_id}")
async def room(
    websocket: WebSocket,
    room_id: int,
    nickname: str = Query("anonymous"),
    user_agent: str = Header(None),
):
    await websocket.accept()
    await websocket.send_json({"room": room_id, "nickname": nickname})
```

If validation fails, the connection is rejected before the handler runs. `Body`, `Form` and `File` parameters aren't allowed: a handshake has no body. Use `receive_json()` instead.

## Validating messages with schemas

Pass `schema=` to validate incoming messages (any type pydantic accepts) or to serialize outgoing data, like `response=` does for HTTP operations:

```python
from typing import List

import pydantic

from ninja import Schema


class Message(Schema):
    text: str


class UserOut(Schema):
    id: int
    username: str


@api.websocket("/messages")
async def messages(websocket: WebSocket):
    await websocket.accept()
    async for message in websocket.iter_json(schema=Message):
        await websocket.send_json(message)  # a Message instance


@api.websocket("/bulk")
async def bulk(websocket: WebSocket):
    await websocket.accept()
    try:
        items = await websocket.receive_json(schema=List[Message])
    except pydantic.ValidationError as e:
        await websocket.send_json({"errors": e.errors(include_url=False)})
        return
    users = [u async for u in User.objects.all()]
    await websocket.send_json(users, schema=List[UserOut])
```

## Authentication

The usual `auth=` argument works, including inheritance from the router or the `NinjaAPI` instance. Pass `auth=None` to make a websocket public when the API has global auth. Authentication runs during the handshake, before the handler:

```python
from ninja.security import APIKeyQuery


class TokenAuth(APIKeyQuery):
    param_name = "token"

    def authenticate(self, request, key):
        return Token.objects.filter(key=key).first()  # sync code is fine


@api.websocket("/notifications", auth=TokenAuth())
async def notifications(websocket: WebSocket):
    token = websocket.auth
    await websocket.accept()
    ...
```

```
ws://localhost:8000/api/notifications?token=abc123
```

Browsers can't set custom headers on a WebSocket, so the token usually goes in the query string or in a cookie.

* Sync auth callbacks run in a thread (`sync_to_async`), so they can use the ORM.
* `django_auth` / `SessionAuth` work: the handshake request has lazy `session` and `user` attributes, filled from the session cookie. Django middlewares don't run for websockets.
* **Cookie-based auth is protected against cross-site WebSocket hijacking.** When `APIKeyCookie` (or `django_auth`) has CSRF enabled, the `Origin` header must match the request host or be listed in `CSRF_TRUSTED_ORIGINS`.

If authentication or validation fails, the client receives an HTTP error (401, 403, 422) with a JSON body, as long as the server supports the `websocket.http.response` ASGI extension. Otherwise the connection is closed with code `1008` and the server answers the handshake with 403.

!!! warning "Use the ORM through async methods"
    Handlers run in the event loop. Use the async ORM API (`aget`, `acreate`, `async for`...) or `sync_to_async`, as described in [Async support](async.md).
    For example, use `await sync_to_async(lambda: websocket.request.user.username)()`.

## Routers

`Router` has the same `websocket()` decorator, and routes get the router prefix:

```python
router = Router()


@router.websocket("/live")
async def live(websocket: WebSocket):
    ...


api.add_router("/events", router)  # ws://.../api/events/live
```

An HTTP operation and a websocket can share the same path.

## Testing

`TestClient` and `TestAsyncClient` have a `websocket_connect()` method that runs the connection in memory, with no server:

```python
from ninja import WebSocketDisconnect
from ninja.testing import TestClient, WebSocketDenied


def test_echo():
    client = TestClient(api)
    with client.websocket_connect("/echo") as ws:
        ws.send_text("hi")
        assert ws.receive_text() == "echo: hi"


def test_auth_required():
    client = TestClient(api)
    with pytest.raises(WebSocketDenied) as exc:
        with client.websocket_connect("/notifications?token=wrong"):
            pass
    assert exc.value.status_code == 401
```

```python
@pytest.mark.asyncio
async def test_echo_async():
    client = TestAsyncClient(api)
    async with client.websocket_connect("/echo") as ws:
        await ws.send_text("hi")
        assert await ws.receive_text() == "echo: hi"
```

`websocket_connect()` accepts `headers=`, `cookies=` and `subprotocols=`. If the handler raises an exception, the test re-raises it.

!!! note
    Database code that runs through `sync_to_async` uses a different thread. With pytest-django, use `@pytest.mark.django_db(transaction=True)` so that data created in the test is visible there.

## Using it with Django Channels

`NinjaASGI()` without an inner application handles only websockets, so you can plug it into an existing Channels `ProtocolTypeRouter`:

```python
from channels.routing import ProtocolTypeRouter
from django.core.asgi import get_asgi_application

from ninja.asgi import NinjaASGI

application = ProtocolTypeRouter({
    "http": get_asgi_application(),
    "websocket": NinjaASGI(),
})
```

## Limitations

* Websocket routes aren't part of the OpenAPI schema (OpenAPI can't describe websockets).
* Django middlewares and `add_decorator()` don't apply to websocket handlers. Throttling isn't supported yet.
* Broadcasting between connections across several processes needs your own pub/sub layer, for example Redis or PostgreSQL `LISTEN/NOTIFY`.
