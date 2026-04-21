# Auto-generated Model API

**Django Ninja** can automatically generate a full set of CRUD endpoints for any Django model with a single method call.

```python
router.add_model_api(MyModel)
```

This registers **6 endpoints** at once, covering every standard CRUD operation — no boilerplate required.

## Generated endpoints

Given a model named `Category`, the following routes are registered (relative to the router prefix):

| Method   | Path               | Action          | Status |
|----------|--------------------|-----------------|--------|
| `GET`    | `/category/`       | List all        | 200    |
| `POST`   | `/category/`       | Create          | 201    |
| `GET`    | `/category/{id}`   | Retrieve by PK  | 200    |
| `PUT`    | `/category/{id}`   | Full update     | 200    |
| `PATCH`  | `/category/{id}`   | Partial update  | 200    |
| `DELETE` | `/category/{id}`   | Delete          | 204    |

The URL prefix is derived automatically from the lowercase model name.

## Quick start

```python
# myapp/api.py
from ninja import Router
from .models import Category

router = Router()
router.add_model_api(Category)
```

Mount the router in your main API file:

```python
# myproject/api.py
from ninja import NinjaAPI
from myapp.api import router as category_router

api = NinjaAPI()
api.add_router("", category_router)
```

Open `/api/docs` and you will see all six operations, complete with request/response schemas, ready to use.

## Generated schemas

Three Pydantic schemas are created automatically:

| Schema                  | Used by            | Includes PK | All fields optional |
|-------------------------|--------------------|-------------|---------------------|
| `CategorySchema`        | List, Retrieve responses | Yes     | No                  |
| `CategoryCreateSchema`  | POST / PUT body    | No          | No                  |
| `CategoryPatchSchema`   | PATCH body         | No          | Yes (all optional)  |

The schemas are derived from the model using [`create_schema`](response/django-pydantic-create-schema.md).

## Parameters

### `fields`

Limit which model fields are included in the schemas. By default all fields are included.

```python
router.add_model_api(Article, fields=["title", "body"])
```

### `exclude`

Remove specific fields from all three schemas.

```python
router.add_model_api(Order, exclude=["internal_notes", "cost_price"])
```

### `operations`

Restrict which CRUD operations are registered. Available values:
`"list"`, `"retrieve"`, `"create"`, `"update"`, `"patch"`, `"delete"`.

```python
# Read-only API — no writes allowed
router.add_model_api(Product, operations=["list", "retrieve"])
```

### `tags`

Override the OpenAPI tags applied to every generated operation. Defaults to the model class name.

```python
router.add_model_api(Category, tags=["catalog", "shop"])
```

### `auth`

Apply an authenticator to every generated operation.

```python
from ninja.security import django_auth

router.add_model_api(Order, auth=django_auth)
```

## Full example

```python
from ninja import NinjaAPI, Router
from ninja.security import django_auth
from myapp.models import Article

api = NinjaAPI()
router = Router()

router.add_model_api(
    Article,
    exclude=["internal_notes"],
    operations=["list", "retrieve", "create", "update", "patch", "delete"],
    tags=["articles"],
    auth=django_auth,
)

api.add_router("", router)
```

---

## Async variant

`add_async_model_api` generates **identical routes and schemas** but every view function is `async def`, taking full advantage of Django's async ORM (Django 4.1+).

```python
router.add_async_model_api(Category)
```

All parameters (`fields`, `exclude`, `operations`, `tags`, `auth`) work exactly the same way.

### When to use the async variant

Use `add_async_model_api` when:

- Your project is deployed with an ASGI server (Uvicorn, Daphne, Hypercorn).
- You expect high concurrency on these endpoints.
- The rest of your API already uses `async def` views.

Use `add_model_api` (sync) when:

- You are using a WSGI server (gunicorn, uWSGI).
- You are on Django < 4.1 (async ORM is not available).

### Example

```python
# myapp/api.py
from ninja import Router
from .models import Category

router = Router()
router.add_async_model_api(Category)
```

!!! note
    Both `add_model_api` and `add_async_model_api` produce identical OpenAPI schemas.
    You can switch between them without changing your frontend or API clients.

## Comparison with manual CRUD

The auto-generated API is equivalent to writing this manually:

```python
from typing import List
from django.http import HttpResponse
from django.shortcuts import get_object_or_404
from ninja import Router, Schema
from myapp.models import Category

router = Router()


class CategorySchema(Schema):
    id: int
    title: str


class CategoryCreateSchema(Schema):
    title: str


class CategoryPatchSchema(Schema):
    title: str | None = None


@router.get("/category/", response=List[CategorySchema])
def list_category(request):
    return Category.objects.all()


@router.post("/category/", response={201: CategorySchema})
def create_category(request, payload: CategoryCreateSchema):
    instance = Category(**payload.dict())
    instance.save()
    return 201, instance


@router.get("/category/{id}", response=CategorySchema)
def retrieve_category(request, id: int):
    return get_object_or_404(Category, pk=id)


@router.put("/category/{id}", response=CategorySchema)
def update_category(request, id: int, payload: CategoryCreateSchema):
    instance = get_object_or_404(Category, pk=id)
    for attr, value in payload.dict().items():
        setattr(instance, attr, value)
    instance.save()
    return instance


@router.patch("/category/{id}", response=CategorySchema)
def partial_update_category(request, id: int, payload: CategoryPatchSchema):
    instance = get_object_or_404(Category, pk=id)
    for attr, value in payload.dict(exclude_unset=True).items():
        setattr(instance, attr, value)
    instance.save()
    return instance


@router.delete("/category/{id}")
def delete_category(request, id: int):
    instance = get_object_or_404(Category, pk=id)
    instance.delete()
    return HttpResponse(status=204)
```

`add_model_api` handles all of the above — plus M2M field updates — in one line.
