# About Django Ninja

!!! quote
    **Django Ninja** looks basically the same as **FastAPI**, so why not just use FastAPI?

Django Ninja is heavily inspired by <a href="https://fastapi.tiangolo.com/" target="_blank">FastAPI</a> (by <a href="https://github.com/tiangolo" target="_blank">Sebastián Ramírez</a>): the same type-hint driven style, Pydantic validation and automatic OpenAPI docs. The difference is where it lives. FastAPI is a standalone framework, and Django Ninja is built for Django.

|                            | FastAPI                                                  | Django Ninja                                             |
| -------------------------- | -------------------------------------------------------- | -------------------------------------------------------- |
| Database                   | ORM-agnostic, so you manage sessions and connections     | Django ORM, with connections managed by Django           |
| Auth and request context   | `Depends(...)` arguments on every endpoint               | `request.auth` / `request.user`, `auth=` set once        |
| Schemas                    | Pydantic "models" (clashes with Django's `Model`)        | `Schema`, plus `ModelSchema` generated from your models  |
| Admin, migrations, users…  | Bring your own                                           | Django's, unchanged                                      |
| Existing Django project    | A second service next to it                              | Mounted in `urls.py`, next to your views                 |

## Why not FastAPI with Django?

**The ORM.** FastAPI is ORM-agnostic, but the Django ORM expects Django to manage database connections around each request. Used from FastAPI, it runs into problems such as [closed connections](https://github.com/tiangolo/fastapi/issues/716) that take real effort to work around.

**Dependency injection gets verbose.** When nearly every operation needs the current user and a database session, those dependencies are repeated in every signature:

=== "FastAPI"

    ```python hl_lines="4 5"
    @app.get("/tasks/{task_id}", response_model=Task)
    def task_details(
        task_id: int,
        db: Session = Depends(get_db),
        current_user: User = Depends(get_current_user),
    ):
        ...
    ```

=== "Django Ninja"

    ```python
    @api.get("/tasks/{task_id}", response=TaskSchema, auth=django_auth)
    def task_details(request, task_id: int):
        return get_object_or_404(Task, id=task_id, owner=request.auth)
    ```

Django Ninja uses the `request` object instead, just like a regular Django view. Authentication can be set once on the API or a router and applies to every operation below it (see [Authentication](guide/authentication.md)).

**Naming.** In Django, "model" means an ORM model. Mixing that with Pydantic's `BaseModel` gets confusing fast, so Django Ninja calls its Pydantic classes **`Schema`**.

## What you get with Django Ninja

**The whole Django ecosystem.** The admin, migrations, users, groups and permissions, sessions, middleware, i18n and any `django-*` package keep working. Nothing needs to be rebuilt or bolted on.

**Drop it into an existing project.** An API is just another entry in `urls.py`. It can live next to your existing views or Django REST Framework, so you can adopt it one endpoint at a time without a second service:

```python
urlpatterns = [
    path("admin/", admin.site.urls),
    path("api/v1/", include(drf_router.urls)),  # existing DRF API
    path("api/v2/", api.urls),                  # new Django Ninja API
]
```

**Multiple APIs in one project.** Each `NinjaAPI` instance has its own version, auth and URL namespace (see [Versioning](guide/versioning.md)):

```python
api_v1 = NinjaAPI(version="1.0", auth=token_auth)
api_v2 = NinjaAPI(version="2.0", auth=token_auth)
api_private = NinjaAPI(auth=django_auth, urls_namespace="private_api")

urlpatterns = [
    path("api/v1/", api_v1.urls),
    path("api/v2/", api_v2.urls),
    path("internal-api/", api_private.urls),
]
```

**Schemas that understand the ORM.** Return querysets or model instances directly (see [Returning querysets](guide/responses.md#returning-querysets)), and generate schemas from your models with [ModelSchema](guide/model-schema.md):

```python
class TaskSchema(ModelSchema):
    class Meta:
        model = Task
        fields = ["id", "title", "completed"]


@api.get("/tasks", response=list[TaskSchema])
def tasks(request):
    return Task.objects.all()
```

## Who is behind it

Django Ninja was started in 2020 by Vitaliy Kucheryaviy at [Code-on](https://code-on.be/), a Django web design and development studio, to handle the API challenges of client projects.

Today it is a production-ready project with 9,000+ GitHub stars, around 190 contributors and over 3 million downloads a month on PyPI.
