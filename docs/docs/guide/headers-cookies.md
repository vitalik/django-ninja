# Headers & Cookies

Request headers and cookies work exactly like [query parameters](query-params.md)
— annotate a function argument with `Header` or `Cookie` and **Django Ninja**
parses, validates and documents it for you.

## Reading a header

```python hl_lines="7"
from ninja import Header, NinjaAPI

api = NinjaAPI()


@api.get("/agent")
def get_agent(request, user_agent: str = Header(...)):
    return {"user_agent": user_agent}
```

The parameter name is matched against the header name **case-insensitively,
with underscores treated as hyphens** — `user_agent` matches the
`User-Agent` header without any extra configuration. This comes straight
from Django's `HttpRequest.headers`, which `Header()` reads from.

## Reading a cookie

```python hl_lines="7"
from ninja import Cookie, NinjaAPI

api = NinjaAPI()


@api.get("/session")
def get_session(request, session_id: str = Cookie(...)):
    return {"session_id": session_id}
```

Unlike headers, cookie names are matched **exactly** — they come straight
from `request.COOKIES`, a plain `dict` with no case- or hyphen-folding. If
your cookie name isn't a valid Python identifier (or just differs from the
argument name), use `alias` (see below).

## Required vs. optional

A parameter with no default is required; **Django Ninja** returns a `422`
if it's missing:

```json
{
    "detail": [
        {
            "type": "missing",
            "loc": ["header", "user_agent"],
            "msg": "Field required"
        }
    ]
}
```

Give it a default to make it optional — combine with `X | None` when the
header genuinely might not be sent:

```python hl_lines="2"
@api.get("/agent")
def get_agent(request, user_agent: str | None = Header(None)):
    return {"user_agent": user_agent}
```

## Type conversion

Like query and path parameters, the type hint drives parsing — headers and
cookies are always sent as strings, but **Django Ninja** converts them for
you:

```python hl_lines="2"
@api.get("/rate-limit")
def rate_limit(request, x_rate_limit: int = Header(100)):
    return {"x_rate_limit": x_rate_limit}
```

`GET /api/rate-limit` with a header `X-Rate-Limit: 42` returns
`{"x_rate_limit": 42}` as a real `int`.

## Aliases

Use `alias` when the header or cookie name isn't a valid Python identifier
even after underscore/hyphen folding, or when you'd simply rather name the
argument something else:

```python hl_lines="2 7"
@api.get("/request-id")
def request_id(request, req_id: str = Header(..., alias="X-Request-ID")):
    return {"request_id": req_id}


@api.get("/weapon")
def weapon(request, weapon: str = Cookie(..., alias="preferred-weapon")):
    return {"weapon": weapon}
```

## Grouping into a Schema

For more than a couple of headers or cookies, group them into a
[`Schema`](schemas.md) — every field is read from its own header/cookie,
using the field's name (or its `alias`) as the key:

```python hl_lines="1-2 7-9 13"
from ninja import Header, NinjaAPI, Schema
from pydantic import Field

api = NinjaAPI()


class ClientInfo(Schema):
    user_agent: str = Field(None, alias="User-Agent")
    x_request_id: str | None = None


@api.get("/client-info")
def client_info(request, client: Header[ClientInfo]):
    return client.model_dump()
```

`client: Header[ClientInfo]` is equivalent to `client: ClientInfo =
Header(...)` — use whichever reads better. The same works with `Cookie[...]`
for a group of cookies. You can mix a header/cookie schema with plain
parameters and other sources (query, path, body) in the same operation —
**Django Ninja** merges them all before calling your view.

## Validation constraints

`Header()` and `Cookie()` accept the same validation and metadata arguments
as [`Query`](query-params.md#validation-constraints): `gt`, `ge`, `lt`, `le`
for numbers, `min_length`, `max_length`, `pattern` for strings, plus `title`,
`description`, `example`/`examples`, `deprecated` and `include_in_schema`
for the generated OpenAPI schema:

```python hl_lines="3"
@api.get("/token")
def token(
    request, x_api_token: str = Header(..., min_length=32, max_length=64)
):
    return {"x_api_token": x_api_token}
```

## Accessing the request directly

`Header`/`Cookie` cover the common case, but the raw values are always on
`request` too — useful for headers you don't want documented, or for
looping over everything at once:

```python
@api.get("/debug")
def debug(request):
    return {
        "headers": dict(request.headers),
        "cookies": request.COOKIES,
    }
```

!!! tip
    Headers and cookies that aren't declared on the operation are simply
    ignored — you don't need to enumerate every key the client might send,
    only the ones you actually read.

!!! note
    This page covers *reading* request headers and cookies. To set response
    headers, cookies or status code from inside a view, see [Headers,
    Cookies & Temporal Response](temporal-response.md).
