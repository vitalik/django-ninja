# Part 1: Project setup & layout

Over eight parts, you'll build **TaskFlow**, a task tracker for teams: projects, members, tasks, labels, comments and file attachments. This first part sets up a project layout that stays tidy as the API grows. Each app gets its own router and schemas, and one small module wires them together.

!!! abstract "What you'll learn"
    - How to lay out a multi-app project: one `Router` per app, one `NinjaAPI` for the project
    - How to mount routers with `add_router()` and group them in the docs with tags
    - How to generate input and output schemas with `ModelSchema`
    - How to nest one app's endpoints under another app's URL, with `Path[...]` for prefix parameters

    **Time:** about 15 minutes

## Create the project

You'll need Django and Django Ninja, and nothing else:

```console
pip install django-ninja
django-admin startproject taskflow .
python manage.py startapp projects
python manage.py startapp tasks
```

TaskFlow doesn't use Django's template views, so you can delete `views.py` and `tests.py` from both apps. The tests come back in Part 7, in their own place.

Register the apps in `taskflow/settings.py`:

```python title="taskflow/settings.py" hl_lines="8-10"
INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'ninja',
    'projects',
    'tasks',
]
```

`'ninja'` is optional. With it, `runserver` serves the Swagger UI assets locally instead of from a CDN.

When this part is done, the project will look like this:

```text
taskflow/
├── api.py          # NinjaAPI: wires the routers together
├── settings.py
└── urls.py
projects/
├── api.py          # Router with the project endpoints
├── models.py
└── schemas.py
tasks/
├── api.py          # Router with the task endpoints
├── models.py
└── schemas.py
manage.py
```

The pattern is the same for every app: models in `models.py`, schemas in `schemas.py`, endpoints in `api.py`. The project package holds only the wiring.

## Models

A project, and a task that belongs to one:

```python title="projects/models.py"
from django.db import models


class Project(models.Model):
    name = models.CharField(max_length=100)
    description = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.name
```

```python title="tasks/models.py"
from django.db import models

from projects.models import Project


class Task(models.Model):
    project = models.ForeignKey(Project, related_name="tasks", on_delete=models.CASCADE)
    title = models.CharField(max_length=200)
    description = models.TextField(default="")
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.title
```

```console
$ python manage.py makemigrations
Migrations for 'projects':
  projects/migrations/0001_initial.py
    + Create model Project
Migrations for 'tasks':
  tasks/migrations/0001_initial.py
    + Create model Task
$ python manage.py migrate
```

Tasks will get assignees, labels, a status and more in later parts. For now, a title is enough.

## Schemas

Each app keeps its schemas in `schemas.py`. As in the Quick Start, there's an `In` schema for what clients send and an `Out` schema for what they get back:

```python title="projects/schemas.py"
from ninja import ModelSchema

from .models import Project


class ProjectIn(ModelSchema):
    class Meta:
        model = Project
        fields = ["name", "description"]


class ProjectOut(ModelSchema):
    class Meta:
        model = Project
        fields = ["id", "name", "description", "created_at"]
```

`ProjectIn` is generated entirely from the model. Neither `name` nor `description` has a default, so both are required.

The task schemas follow the same pattern:

```python title="tasks/schemas.py"
from ninja import ModelSchema

from .models import Task


class TaskIn(ModelSchema):
    class Meta:
        model = Task
        fields = ["title", "description"]


class TaskOut(ModelSchema):
    class Meta:
        model = Task
        fields = ["id", "project", "title", "description", "created_at"]
```

`Task.description` has `default=""`, so `TaskIn` makes it optional, with an empty string as the default. `TaskIn` has no `project` field. The project comes from the URL, as you'll see below. In `TaskOut`, the `project` foreign key is serialized as the project's id. Part 2 replaces ids like this with nested objects where that helps.

**Go deeper:** [ModelSchema](../guide/model-schema.md#basic-usage)

## The projects router

Each app's endpoints live on a `Router` in the app's `api.py`. Here's full CRUD for projects:

```python title="projects/api.py" hl_lines="7 17 37"
from django.shortcuts import get_object_or_404
from ninja import Router, Status

from .models import Project
from .schemas import ProjectIn, ProjectOut

router = Router(tags=["projects"])


@router.get("/", response=list[ProjectOut])
def list_projects(request):
    return Project.objects.order_by("id")


@router.post("/", response={201: ProjectOut})
def create_project(request, payload: ProjectIn):
    return Status(201, Project.objects.create(**payload.dict()))


@router.get("/{project_id}", response=ProjectOut)
def get_project(request, project_id: int):
    return get_object_or_404(Project, id=project_id)


@router.put("/{project_id}", response=ProjectOut)
def update_project(request, project_id: int, payload: ProjectIn):
    project = get_object_or_404(Project, id=project_id)
    for attr, value in payload.dict().items():
        setattr(project, attr, value)
    project.save()
    return project


@router.delete("/{project_id}", response={204: None})
def delete_project(request, project_id: int):
    get_object_or_404(Project, id=project_id).delete()
    return Status(204, None)
```

- The router doesn't know where it will be mounted. Its paths are relative (`/`, `/{project_id}`), and the prefix is set when the project wires it in.
- `tags=["projects"]` applies to every operation on the router. The interactive docs group endpoints by tag, so each app gets its own section.
- `Status(201, ...)` picks the status code from the ones declared in `response=`. `Status(204, None)` sends an empty response.

!!! note
    The Quick Start returned `(status, body)` tuples. They still work, but they're deprecated in favor of `Status(...)`, which is what TaskFlow uses throughout.

**Go deeper:** [Routers](../guide/routers.md#basic-usage), [Responses](../guide/responses.md#empty-responses)

## Wire the routers together

The project-level `api.py` creates the `NinjaAPI` and mounts each app's router under a prefix:

```python title="taskflow/api.py" hl_lines="5-6"
from ninja import NinjaAPI

api = NinjaAPI(title="TaskFlow API")

api.add_router("/projects", "projects.api.router")
api.add_router("/projects/{project_id}/tasks", "tasks.api.router")
```

`add_router()` accepts the router object or its dotted import path. With the string form, `taskflow/api.py` has no imports from the apps, and each router module is imported only when `add_router()` runs. As the apps start importing each other's models, that helps you avoid circular imports.

`urls.py` mounts the API once, like any other set of views:

```python title="taskflow/urls.py"
from django.contrib import admin
from django.urls import path

from .api import api

urlpatterns = [
    path("admin/", admin.site.urls),
    path("api/", api.urls),
]
```

The project routes now live at `/api/projects/` and `/api/projects/{project_id}`.

**Go deeper:** [The NinjaAPI Instance](../guide/api.md#adding-routers)

## Tasks under a project

Tasks always belong to a project, so their URLs sit under it: `/api/projects/{project_id}/tasks/`. The second `add_router()` call above sets that up. Its prefix contains a `{project_id}` placeholder, and every operation on the tasks router can read it:

```python title="tasks/api.py" hl_lines="13 19 25"
from django.shortcuts import get_object_or_404
from ninja import Path, Router, Status

from projects.models import Project

from .models import Task
from .schemas import TaskIn, TaskOut

router = Router(tags=["tasks"])


@router.get("/", response=list[TaskOut])
def list_tasks(request, project_id: Path[int]):
    project = get_object_or_404(Project, id=project_id)
    return project.tasks.order_by("id")


@router.post("/", response={201: TaskOut})
def create_task(request, project_id: Path[int], payload: TaskIn):
    project = get_object_or_404(Project, id=project_id)
    return Status(201, Task.objects.create(project=project, **payload.dict()))


@router.get("/{task_id}", response=TaskOut)
def get_task(request, project_id: Path[int], task_id: int):
    return get_object_or_404(Task, id=task_id, project_id=project_id)
```

- `project_id: Path[int]` reads the value from the URL prefix and converts it to an `int`.
- `task_id` is part of the operation's own path (`/{task_id}`), so a plain `int` is enough, like `project_id` in the projects router.
- `create_task` takes the project from the URL, not from the body. A client can't create a task in one project by posting it to another project's URL.
- `get_task` filters on both ids, so `/projects/3/tasks/2` returns 404 when task 2 belongs to project 1.

!!! warning "Don't forget `Path[...]` on prefix parameters"
    Django Ninja only treats an argument as a path parameter automatically if it appears in the operation's **own** path. It doesn't look at the router's prefix. If you write `project_id: int` in `list_tasks`, it becomes a required **query** parameter. The docs then ask for `?project_id=`, and the `{project_id}` in the URL is ignored. `GET /api/projects/1/tasks/` fails:

    ```json
    {
        "detail": [
            {
                "type": "missing",
                "loc": ["query", "project_id"],
                "msg": "Field required"
            }
        ]
    }
    ```

    With `Path[int]`, the value is read from the URL where it belongs.

### Why not a nested router?

You could get the same URLs by nesting routers inside the projects app:

```python
router.add_router("/{project_id}/tasks", tasks_router)
```

That works, but the projects app would then have to import the tasks app. Mounting both routers in `taskflow/api.py` keeps each app self-contained, and all the URL structure is in one file. Nested routers make more sense for sub-routers of a single app.

**Go deeper:** [Path Parameters](../guide/path-params.md#path-parameters-from-a-router-prefix), [Routers](../guide/routers.md#nested-url-parameters)

## Try it

```console
python manage.py runserver
```

Create a project with `POST /api/projects/`. The body is `{"name": "Website redesign", "description": "New marketing site"}`, and the response is `201`:

```json
{
    "id": 1,
    "name": "Website redesign",
    "description": "New marketing site",
    "created_at": "2026-09-29T09:30:27.635Z"
}
```

A second project, `{"name": "Mobile app", "description": "iOS and Android"}`, gets id 2:

```json
{
    "id": 2,
    "name": "Mobile app",
    "description": "iOS and Android",
    "created_at": "2026-09-29T09:30:27.636Z"
}
```

Leave out the required fields, as in `{}`, and you get a `422` that points at each missing one:

```json
{
    "detail": [
        {
            "type": "missing",
            "loc": ["body", "payload", "name"],
            "msg": "Field required"
        },
        {
            "type": "missing",
            "loc": ["body", "payload", "description"],
            "msg": "Field required"
        }
    ]
}
```

Now add two tasks to project 1. `POST /api/projects/1/tasks/` with `{"title": "Draft the sitemap"}`, then again with `{"title": "Pick a color palette", "description": "Two options"}`. `GET /api/projects/1/tasks/` lists them:

```json
[
    {
        "id": 1,
        "project": 1,
        "title": "Draft the sitemap",
        "description": "",
        "created_at": "2026-09-29T09:30:27.647Z"
    },
    {
        "id": 2,
        "project": 1,
        "title": "Pick a color palette",
        "description": "Two options",
        "created_at": "2026-09-29T09:30:27.649Z"
    }
]
```

Unknown ids, whether a missing project or a task under the wrong project, return a `404`. `GET /api/projects/3/tasks/2`:

```json
{
    "detail": "Not Found: No Task matches the given query."
}
```

The message after `Not Found` only appears with `DEBUG = True`. In production, the body is just `{"detail": "Not Found"}`.

Open <http://127.0.0.1:8000/api/docs>. The page title is **TaskFlow API**, and the endpoints are grouped under **projects** and **tasks**. Here's the full list, with where each parameter comes from:

```text
GET    /api/projects/                           ['projects']
POST   /api/projects/                           ['projects']
GET    /api/projects/{project_id}               ['projects']  project_id (path)
PUT    /api/projects/{project_id}               ['projects']  project_id (path)
DELETE /api/projects/{project_id}               ['projects']  project_id (path)
GET    /api/projects/{project_id}/tasks/        ['tasks']  project_id (path)
POST   /api/projects/{project_id}/tasks/        ['tasks']  project_id (path)
GET    /api/projects/{project_id}/tasks/{task_id} ['tasks']  project_id (path), task_id (path)
```

**Go deeper:** [OpenAPI & Interactive Docs](../guide/openapi.md), [Errors & Exception Handling](../guide/errors.md#default-exception-handlers)

## Recap

- Each app owns a `Router` in `api.py` and its schemas in `schemas.py`. `taskflow/api.py` only creates the `NinjaAPI` and mounts routers.
- `add_router()` sets the prefix and accepts a dotted path, which helps avoid circular imports. `Router(tags=[...])` groups each app's endpoints in the docs.
- `ModelSchema` generates schemas from models. A model field without a default is required in the schema, and `default=""` makes it optional.
- A router mounted under `/projects/{project_id}/tasks` reads the prefix parameter with `project_id: Path[int]`. Without `Path`, it would become a query parameter.
- `Status(code, body)` picks the response status code.

## Next

Tasks are still flat records. In [Part 2: Relations & computed fields](part-2.md), you'll add assignees and labels, return nested objects, compute task counts, and keep the number of queries under control.
