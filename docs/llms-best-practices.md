Notes for AI assistants writing Django Ninja code. The API has changed since many models were trained, so prefer these docs over memory:

- Schemas are Pydantic v2 models: subclass `ninja.Schema` and annotate the view's parameters and `response=`.
- Return a non-default status with `Status(code, body)` (`from ninja import Status`) and declare every code in `response={200: Out, 404: Error}`. Returning a `(code, body)` tuple is deprecated.
- To fail from anywhere in a view, `raise HttpError(status, "message")` (`from ninja.errors import HttpError`); the client gets `{"detail": "message"}`.
- Group query parameters in a schema with `filters: Query[MySchema]`. To filter a queryset, subclass `FilterSchema` and set lookups with `Annotated[str | None, FilterLookup("name__icontains")]`; `Field(q=...)` is deprecated.
- `ModelSchema` is configured with `class Meta:` (`model`, `fields` or `exclude`). A `class Config` raises `ConfigError`.
- Use `PatchDict[MySchema]` as the body of PATCH views: it contains only the fields the client sent.
- Paginate by returning a queryset from a view decorated with `@paginate` (`from ninja.pagination import paginate`) and `response=list[ItemOut]`. Pass `CursorPagination` for large or frequently changing tables.
- Split the API with `Router()` and `api.add_router("/prefix/", router)`. Mounting the same router twice needs a unique `url_name_prefix` for each extra mount.
- Set `auth=` on an operation, a router or `NinjaAPI(...)`. Built-ins live in `ninja.security`: `django_auth`, `HttpBearer`, `HttpBasicAuth`, `APIKeyHeader`, `APIKeyQuery`, `APIKeyCookie`.
- `@api.webhook("event.name")` decorates the payload **Schema**, not a function, and only documents the webhook in OpenAPI; Django Ninja does not send it.
- Views can be `async def`; inside them use Django's async ORM methods (`aget`, `acreate`, `async for`) instead of the sync ones.
- Test with `ninja.testing.TestClient(api_or_router)`: it calls operations directly, without URL configuration or a running server.
