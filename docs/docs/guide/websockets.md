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

## Setup: an ASGI server

WebSockets only work with an **ASGI** server such as [uvicorn](https://www.uvicorn.org/), [daphne](https://github.com/django/daphne) or [hypercorn](https://hypercorn.readthedocs.io/). WSGI servers (gunicorn sync workers, `mod_wsgi`, `manage.py runserver` without daphne) can't handle them.

Django's own ASGI handler only speaks HTTP, so in `asgi.py` replace `django.core.asgi.get_asgi_application` with the one from `ninja.asgi`:

```python title="asgi.py" hl_lines="3 6"
import os

from ninja.asgi import get_asgi_application

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "mysite.settings")
application = get_asgi_application()
```

It's a drop-in replacement: it wraps Django's application, so HTTP requests still go to Django as before. If you prefer to make the wrapping explicit (or need to wrap another ASGI application), use `NinjaASGI`:

```python
from django.core.asgi import get_asgi_application

from ninja.asgi import NinjaASGI

application = NinjaASGI(get_asgi_application())
```

WebSocket connections are resolved against your `urls.py`, where websocket routes are added through `api.urls`, like any other operation:

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
    The websocket path also exists as an HTTP URL, and it answers **426 Upgrade Required**. If an upgrade request reaches Django's HTTP stack (for example through a WSGI server), the response body explains that an ASGI server and `ninja.asgi` are required.

## The `WebSocket` object

A websocket handler is an `async def` function with a parameter annotated as `WebSocket` (any name works). Handlers don't receive a `request` argument; the handshake request is available as `websocket.request`.

| Method / attribute | Description |
| --- | --- |
| `await websocket.accept(subprotocol=None, headers=None)` | Accept the connection |
| `await websocket.receive_text()` / `receive_bytes()` | Receive a message |
| `await websocket.receive_json(mode="text", schema=None)` | Receive and decode JSON, optionally [validated with a schema](#validating-messages-with-schemas) |
| `await websocket.send_text(data)` / `send_bytes(data)` | Send a message |
| `await websocket.send_json(data, mode="text", schema=None)` | Send JSON, encoded with the API [renderer](renderers.md) (pydantic models are serialized automatically) |
| `websocket.iter_text()` / `iter_bytes()` / `iter_json()` | Async iterators that stop when the client disconnects |
| `await websocket.close(code=1000, reason=None)` | Close the connection |
| `websocket.path`, `path_params`, `query_params`, `headers`, `cookies`, `client`, `subprotocols` | Handshake information |
| `websocket.auth` | The result of the [authentication](#authentication) callback |
| `websocket.request` | A read-only Django `HttpRequest` built from the handshake |

When the client disconnects, `receive_*` raises `WebSocketDisconnect`. The `iter_*` iterators stop instead:

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

If the handler returns while the connection is still open, it is closed with code `1000`.

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

If validation fails, the handshake is rejected with a 422 before the handler runs (see [Errors](#errors)). `Body`, `Form` and `File` parameters aren't allowed: a handshake has no body. Use `receive_json()` instead.

## Validating messages with schemas

Pass `schema=` to validate incoming messages (any type pydantic accepts) or to serialize outgoing data, like `response=` does for HTTP operations:

```python
from typing import List

from ninja import Schema
from ninja.errors import ValidationError


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
    except ValidationError as e:
        await websocket.send_json({"errors": e.errors})
        return
    users = [u async for u in User.objects.all()]  # Django 4.1+
    await websocket.send_json(users, schema=List[UserOut])
```

* Invalid messages raise `ninja.errors.ValidationError`. Its `errors` list has the same JSON-safe format as the body of HTTP 422 responses, so you can send it back to the client. If you don't catch it, the connection is closed with code `1008`.
* With `schema=`, type checkers know the result type: `receive_json(schema=Message)` is a `Message`, and `receive_json(schema=List[Message])` is a `List[Message]`.

## Errors

Exceptions go through the API [exception handlers](errors.md), just like in HTTP operations:

* **Before `accept()`**, the handler's response is sent as the answer to the handshake. For example, `raise HttpError(404, "Room not found")` returns a 404 with the usual JSON body.
* **After `accept()`**, an HTTP response can no longer be sent. The connection is closed with code `1008` and the error `detail` as the reason, or with code `1011` when the status is 5xx.
* **Exceptions that no handler deals with**:
    * the error is logged (logger `ninja.websockets`);
    * Django's `got_request_exception` signal is sent, so error reporting tools such as Sentry see it;
    * the connection is closed with code `1011`.

```python
from ninja.errors import HttpError


@api.websocket("/rooms/{room_id}")
async def room(websocket: WebSocket, room_id: int):
    if not await Room.objects.filter(id=room_id).aexists():  # Django 4.1+
        raise HttpError(404, "Room not found")
    await websocket.accept()
    ...
```

To close the connection with a specific websocket close code, raise `WebSocketException`. It works from the handler and from auth callbacks, before or after `accept()`:

```python
from ninja import WebSocketException

raise WebSocketException(code=4000, reason="Game over")
```

!!! note "Sending HTTP responses during the handshake"
    Sending an HTTP response (401, 404, 422...) to a handshake requires an ASGI server that supports the `websocket.http.response` extension; uvicorn does. Otherwise the connection is closed with code `1008` (`1013` for throttling, `1011` for 5xx) and the error detail as the reason, and the server answers the handshake with 403.

## Authentication

The usual `auth=` argument works, including inheritance from the router or the `NinjaAPI` instance. Pass `auth=None` to make a websocket public when the API has global auth. Authentication runs during the handshake, before the handler:

```python
from ninja.security import APIKeyHeader


class SubprotocolToken(APIKeyHeader):
    """Reads the token sent as `new WebSocket(url, ["access_token", token])`."""

    param_name = "Sec-WebSocket-Protocol"

    def authenticate(self, request, key):
        name, _, token = (key or "").partition(",")
        if name.strip() == "access_token":
            return Token.objects.filter(key=token.strip()).first()  # sync code is fine


@api.websocket("/notifications", auth=SubprotocolToken())
async def notifications(websocket: WebSocket):
    token = websocket.auth
    # browsers require the server to select one of the requested subprotocols
    await websocket.accept(subprotocol="access_token")
    ...
```

```javascript
const ws = new WebSocket("wss://example.com/api/notifications", ["access_token", token]);
```

Browsers can't set custom headers like `Authorization` on a WebSocket. That leaves three ways to send credentials:

* **A subprotocol** (example above): the token travels in the `Sec-WebSocket-Protocol` header.
* **A cookie**: the session cookie with `django_auth`, or `APIKeyCookie`.
* **The query string** (`APIKeyQuery`): simple, but be careful. Servers and proxies write full URLs to their access logs, so the token ends up in those logs. If you use it, prefer short-lived, single-use tickets obtained through an authenticated HTTP endpoint over long-lived API keys.

Good to know:

* Sync auth callbacks run in a thread (`sync_to_async`), so they can use the ORM.
* `django_auth` / `SessionAuth` work: the handshake request has lazy `session` and `user` attributes and an `auser()` method, filled from the session cookie (Django middlewares don't run for websockets).
* Authentication only runs during the handshake. Long-lived connections are not re-checked if the session ends or the token expires. Close them from your own code when that matters.

## Security

### Origin check

Browsers send cookies on cross-site WebSocket handshakes, and the same-origin policy doesn't apply to WebSockets. Without a check, any website could open a connection on behalf of a logged-in user ("cross-site WebSocket hijacking"). So by default **every handshake with an `Origin` header** must come from the request host or from an origin listed in `CSRF_TRUSTED_ORIGINS`; otherwise it is rejected with a 403. Non-browser clients usually don't send `Origin`, and they are not affected.

To accept connections from any website (for example a public widget):

```python
@api.websocket("/public-feed", check_origin=False)
async def public_feed(websocket: WebSocket):
    ...
```

To disable it for the whole project, set `NINJA_WEBSOCKET_CHECK_ORIGIN = False` in settings; routes can still opt in with `check_origin=True`. Cookie auth with CSRF enabled (`django_auth`, `APIKeyCookie()`) always checks the origin.

### Allowed hosts

The `Host` header is validated against `ALLOWED_HOSTS`, as for HTTP requests. Invalid hosts get a 400.

### Throttling

`throttle=` works like in HTTP operations, including inheritance from the router and the API. It limits **new connections** (handshakes), not messages. Throttled handshakes get a 429 with a `Retry-After` header:

```python
from ninja.throttling import AnonRateThrottle


@api.websocket("/live", throttle=AnonRateThrottle("10/m"))
async def live(websocket: WebSocket):
    ...
```

## Using the ORM

Handlers run in the event loop. Use the async ORM API (`aget`, `acreate`, `async for`...) or `sync_to_async`, as described in [Async support](async.md). For example:

```python
user = await websocket.request.auser()  # the logged-in user (session auth)
rooms = [room async for room in Room.objects.filter(owner=user)]  # Django 4.1+
```

By default, `sync_to_async` runs all the sync code in a single shared thread. With many connections making sync database calls at the same time, those calls run one after another; prefer the async ORM methods in busy handlers.

## Routers and URLs

`Router` has the same `websocket()` decorator, and routes get the router prefix:

```python
router = Router()


@router.websocket("/live")
async def live(websocket: WebSocket):
    ...


api.add_router("/events", router)  # ws://.../api/events/live
```

* An HTTP operation and a websocket can share the same path.
* Websocket routes have a url name, like HTTP operations. It defaults to the function name, or you can set it with `url_name=`. So `reverse()` works for them.
* If a websocket gets the same url name as an HTTP route, `api.urls` raises a `ConfigError`. In that case, pass a different `url_name=`.

### Per-request URLconfs

Websocket paths are resolved against `ROOT_URLCONF`, or against the `urlconf=` given to `NinjaASGI`. Some projects choose the URLconf per request in a middleware, for example with django-hosts or django-tenants. Those middlewares don't run for websockets, so override `get_urlconf()` instead:

```python
from ninja.asgi import NinjaASGI


class HostsASGI(NinjaASGI):
    def get_urlconf(self, websocket):
        host = websocket.request.get_host().split(":")[0]
        if host.startswith("api."):
            return "myproject.urls_api"
        return super().get_urlconf(websocket)
```

## Broadcasting

Each connection runs its own handler. To send a message to several clients, keep track of the open connections. In a single process, a set is enough:

```python
import asyncio
from typing import Set

connections: Set[WebSocket] = set()


async def broadcast(message: str) -> None:
    # one slow or broken client must not stop the others
    await asyncio.gather(
        *(conn.send_text(message) for conn in list(connections)),
        return_exceptions=True,
    )


@api.websocket("/chat")
async def chat(websocket: WebSocket):
    await websocket.accept()
    connections.add(websocket)
    try:
        async for message in websocket.iter_text():
            await broadcast(message)
    finally:
        connections.discard(websocket)
```

With several server processes or machines, each process only knows its own connections. In that case you need a pub/sub layer between them, such as Redis or PostgreSQL `LISTEN/NOTIFY`. The handler then publishes messages to it and forwards the messages it receives to its own clients.

## Testing

`TestClient` and `TestAsyncClient` have a `websocket_connect()` method that runs the connection in memory, with no server:

```python
import pytest

from ninja.testing import TestClient, WebSocketDenied


def test_echo():
    client = TestClient(api)
    with client.websocket_connect("/echo") as ws:
        ws.send_text("hi")
        assert ws.receive_text() == "echo: hi"


def test_auth_required():
    client = TestClient(api)
    with pytest.raises(WebSocketDenied) as exc:
        with client.websocket_connect("/notifications", subprotocols=["access_token", "wrong"]):
            pass
    assert exc.value.status_code == 401
```

```python
import pytest

from ninja.testing import TestAsyncClient


@pytest.mark.asyncio
async def test_echo_async():
    client = TestAsyncClient(api)
    async with client.websocket_connect("/echo") as ws:
        await ws.send_text("hi")
        assert await ws.receive_text() == "echo: hi"
```

* `websocket_connect()` accepts `headers=`, `cookies=`, `subprotocols=` and `timeout=`.
* A rejected handshake raises `WebSocketDenied`, which has `status_code`, `headers`, `body` and `json()`.
* If the server closes the connection, `WebSocketDisconnect` is raised.
* If the handler raises an exception, the test re-raises it.

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

## Differences from FastAPI

The `WebSocket` API (`accept`, `receive_*`, `send_*`, `iter_*`, `close`), `WebSocketDisconnect` and `WebSocketException` follow FastAPI/Starlette. Some things differ:

* There is no dependency injection (`Depends`). Use `auth=` and Path/Query/Header/Cookie parameters.
* `websocket.url`, `websocket.state` and `websocket.app` don't exist. Use `websocket.path`, `websocket.query_params` and `websocket.request` instead.
* `receive_json()`, `iter_json()` and `send_json()` take a `schema=` argument for validation.
* Errors go through the API exception handlers (see [Errors](#errors)).

## Limitations

* Websocket routes aren't part of the OpenAPI schema (OpenAPI can't describe websockets).
* Django middlewares don't run for websocket connections.
* Decorators added with `add_decorator()` wrap HTTP views, so they don't apply to websocket handlers. A warning is emitted when an API or router has both.
* Throttling applies to handshakes. To limit messages, count them in your handler.
* There is no built-in broadcasting or groups. See [Broadcasting](#broadcasting) for a single-process example.
