# Guide

This is the reference guide: one topic per page, each covering a single part of Django Ninja completely — how it works, every option, and the edge cases. If you're starting out, do the [Quick Start](../quickstart/index.md) or [Tutorial](../tutorial/index.md) first; come back here when you need the details on a specific feature.

Every page is self-contained and can be read on its own, but the pages build on a few core objects that are worth knowing about upfront.

## The core pieces

- **[`NinjaAPI`](api.md)** — the root object. You create one per project (or one per API version), then wire it into `urls.py`. It's also where you configure global concerns like authentication, throttling, exception handlers, CSRF, OpenAPI/docs URLs and versioning.
- **[Operations](operations.md)** — an operation is a single endpoint: the combination of an HTTP method, a URL path and a Python function (`@api.get(...)`, `@api.post(...)`, etc.).
- **[Routers](routers.md)** — a way to group related operations and mount them under a prefix, similar to Django's own `include()`. Used to split a large API into modules.
- **[Schemas](schemas.md)** — Pydantic models used to declare the shape of request bodies and responses, and to generate the OpenAPI schema and interactive docs automatically.

A minimal API using all four looks like this:

```python
from ninja import NinjaAPI, Router, Schema

api = NinjaAPI()
router = Router()


class HelloResponse(Schema):
    message: str


@router.get("/hello", response=HelloResponse)
def hello(request, name: str = "world"):
    return {"message": f"Hello, {name}"}


api.add_router("/greetings", router)
```

## What's covered

The rest of the guide is grouped by what you're trying to do:

**Handling requests**

- [URLs & Reverse](urls.md) — how paths are built and how to reverse them
- [Path Parameters](path-params.md), [Query Parameters](query-params.md)
- [Request Body](body.md), [Form Data](forms.md), [File Uploads](files.md)
- [Headers & Cookies](headers-cookies.md)
- [Request Parsers](parsers.md) — customizing how the request body is decoded

**Schemas**

- [Schemas](schemas.md) — the base `Schema` class and its configuration
- [ModelSchema](model-schema.md) and [`create_schema`](create-schema.md) — generating schemas from Django models
- [Schema Configuration](schema-config.md)

**Producing responses**

- [Responses](responses.md), [Headers, Cookies & Temporal Response](temporal-response.md)
- [Renderers](renderers.md) — customizing how responses are serialized
- [Pagination](pagination.md), [Filtering](filtering.md)

**Cross-cutting concerns**

- [Authentication](authentication.md), [CSRF](csrf.md), [Throttling](throttling.md)
- [Errors & Exception Handling](errors.md)
- [Decorators](decorators.md) — writing reusable decorators that work with Ninja's signature inspection
- [Async Support](async.md)
- [Versioning](versioning.md)

**Tooling**

- [OpenAPI & Interactive Docs](openapi.md)
- [Webhooks](webhooks.md) — documenting the requests your API sends to other servers
- [Testing](testing.md)
- [Settings](settings.md)
