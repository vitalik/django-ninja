# Part 2: Relations & computed fields

In Part 1, a task was a flat record whose project came back as a bare id. Real tasks have an assignee and labels, and clients want to see who and what those are without making a request for each one. In this part you'll add those relations, return them as nested objects, compute a few values the model doesn't store, and check how many queries each list costs.

!!! abstract "What you'll learn"
    - How to return related objects as nested schemas, while clients send plain ids
    - How to set a many-to-many relation after creating an object
    - How to compute a field with a `resolve_<field>` static method
    - How to read ORM annotations and reverse relations into a schema
    - How to spot N+1 queries and fix them with `select_related` and `prefetch_related`

    **Time:** about 15 minutes

## Assignees and labels

Labels belong to a project, so each project has its own set, like "bug" or "design". The `Label` model goes in the projects app:

```python title="projects/models.py" hl_lines="13-22"
from django.db import models


class Project(models.Model):
    name = models.CharField(max_length=100)
    description = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.name


class Label(models.Model):
    project = models.ForeignKey(Project, related_name="labels", on_delete=models.CASCADE)
    name = models.CharField(max_length=50)
    color = models.CharField(max_length=7, default="#808080")

    class Meta:
        ordering = ["name"]

    def __str__(self):
        return self.name
```

A task gets an optional assignee, which is a Django user, and any number of labels:

```python title="tasks/models.py" hl_lines="11-18"
from django.conf import settings
from django.db import models

from projects.models import Label, Project


class Task(models.Model):
    project = models.ForeignKey(Project, related_name="tasks", on_delete=models.CASCADE)
    title = models.CharField(max_length=200)
    description = models.TextField(default="")
    assignee = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        related_name="assigned_tasks",
        on_delete=models.SET_NULL,
    )
    labels = models.ManyToManyField(Label, blank=True, related_name="tasks")
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.title
```

```console
$ python manage.py makemigrations
Migrations for 'projects':
  projects/migrations/0002_label.py
    + Create model Label
Migrations for 'tasks':
  tasks/migrations/0002_task_assignee_task_labels.py
    + Add field assignee to task
    + Add field labels to task
$ python manage.py migrate
```

TaskFlow has no user endpoints yet; sign-up and login come in Part 4. For now, create two users in the shell. Django's shell imports your models, `User` included, automatically:

```console
$ python manage.py shell
>>> User.objects.create_user("alice", first_name="Alice", last_name="Martin")
<User: alice>
>>> User.objects.create_user("bob")
<User: bob>
```

The examples below start from an empty database, so if you want your ids to match them, delete `db.sqlite3` and run `migrate` again before creating the users.

## Nested output, ids on input

By default, `ModelSchema` turns a foreign key into the related object's id and a many-to-many field into a list of ids. That's the right shape for input, since a client picks an assignee by id. For output, clients usually want the name as well, so they don't have to look it up. The task schemas therefore use ids going in and nested objects coming out:

```python title="tasks/schemas.py" hl_lines="10 16-18 22-23 31-32"
from django.contrib.auth.models import User
from ninja import ModelSchema

from projects.schemas import LabelOut

from .models import Task


class UserOut(ModelSchema):
    display_name: str

    class Meta:
        model = User
        fields = ["id", "username"]

    @staticmethod
    def resolve_display_name(user):
        return user.get_full_name() or user.username


class TaskIn(ModelSchema):
    assignee_id: int | None = None
    label_ids: list[int] = []

    class Meta:
        model = Task
        fields = ["title", "description"]


class TaskOut(ModelSchema):
    assignee: UserOut | None
    labels: list[LabelOut]

    class Meta:
        model = Task
        fields = ["id", "project", "title", "description", "created_at"]
```

- `TaskOut` declares `assignee` and `labels` with other schemas as their types. Django Ninja reads `task.assignee` and serializes it with `UserOut`, or as `null` when it's empty. It reads `task.labels`, a related manager, and turns it into a list of `LabelOut`. You don't need to call `.all()`.
- `TaskIn` takes `assignee_id` and `label_ids`, both optional. `assignee_id` matches the column name Django uses for the foreign key, so it can go straight into `Task.objects.create()`.
- `display_name` isn't a field on `User`. `resolve_display_name` computes it from the object being serialized: the full name if there is one, or else the username. A resolver must be a `@staticmethod` named `resolve_<field>`.

!!! note
    Fields you declare on a `ModelSchema` come first in the output, before the fields from `Meta.fields`. That's why `assignee` and `labels` appear before `id` in the responses below.

`LabelOut` lives next to its model in `projects/schemas.py`, with a `LabelIn` for creating labels:

```python title="projects/schemas.py" hl_lines="6-15 25-27"
from ninja import ModelSchema

from .models import Label, Project


class LabelIn(ModelSchema):
    class Meta:
        model = Label
        fields = ["name", "color"]


class LabelOut(ModelSchema):
    class Meta:
        model = Label
        fields = ["id", "name", "color"]


class ProjectIn(ModelSchema):
    class Meta:
        model = Project
        fields = ["name", "description"]


class ProjectOut(ModelSchema):
    labels: list[LabelOut]
    task_count: int
    unassigned_task_count: int

    class Meta:
        model = Project
        fields = ["id", "name", "description", "created_at"]
```

`color` has a model default, so `LabelIn` makes it optional. The new `ProjectOut` fields are covered in [Computed project fields](#computed-project-fields) below.

**Go deeper:** [Schemas](../guide/schemas.md#nested-schemas-and-lists), [ModelSchema](../guide/model-schema.md#relations)

## Creating tasks with relations

The ids in `TaskIn` come from the client, so check them before you use them. An unknown `assignee_id` would otherwise fail inside the database with an `IntegrityError`, and a label from another project doesn't belong on this task:

```python title="tasks/api.py" hl_lines="14-20 32-34"
from django.contrib.auth.models import User
from django.shortcuts import get_object_or_404
from ninja import Path, Router, Status
from ninja.errors import HttpError

from projects.models import Project

from .models import Task
from .schemas import TaskIn, TaskOut

router = Router(tags=["tasks"])


def check_relations(project, payload):
    if payload.assignee_id is not None and not User.objects.filter(id=payload.assignee_id).exists():
        raise HttpError(400, f"User {payload.assignee_id} does not exist")
    labels = list(project.labels.filter(id__in=payload.label_ids))
    if len(labels) != len(set(payload.label_ids)):
        raise HttpError(400, "Unknown label id for this project")
    return labels


@router.get("/", response=list[TaskOut])
def list_tasks(request, project_id: Path[int]):
    project = get_object_or_404(Project, id=project_id)
    return project.tasks.select_related("assignee").prefetch_related("labels").order_by("id")


@router.post("/", response={201: TaskOut})
def create_task(request, project_id: Path[int], payload: TaskIn):
    project = get_object_or_404(Project, id=project_id)
    labels = check_relations(project, payload)
    task = Task.objects.create(project=project, **payload.dict(exclude={"label_ids"}))
    task.labels.set(labels)
    return Status(201, task)


@router.get("/{task_id}", response=TaskOut)
def get_task(request, project_id: Path[int], task_id: int):
    return get_object_or_404(Task, id=task_id, project_id=project_id)
```

- `check_relations` returns the `Label` objects. It looks them up through `project.labels`, the reverse relation, so labels from other projects are never found.
- `HttpError(400, ...)` stops the request with a `{"detail": ...}` body. Part 3 covers validation and errors in more depth.
- A many-to-many relation needs a saved row, so it's set after `create()`. `payload.dict(exclude={"label_ids"})` leaves out the one key the model doesn't accept.
- The `select_related` and `prefetch_related` calls in `list_tasks` are explained in [Counting queries](#counting-queries).

Labels are created on their project with `POST /api/projects/{project_id}/labels`. That endpoint is `create_label` at the end of `projects/api.py`, shown in full in the next section.

### Try it

Create a project with `POST /api/projects/` and `{"name": "Website redesign", "description": "New marketing site"}`, then add two labels to it: `POST /api/projects/1/labels` with `{"name": "bug", "color": "#d73a4a"}`, then with `{"name": "design"}`. The second label gets the default color:

```json
{
    "id": 2,
    "name": "design",
    "color": "#808080"
}
```

Now create a task. `POST /api/projects/1/tasks/` with `{"title": "Draft the sitemap", "assignee_id": 1, "label_ids": [2]}` returns `201`, with ids in and objects out:

```json
{
    "assignee": {
        "display_name": "Alice Martin",
        "id": 1,
        "username": "alice"
    },
    "labels": [
        {
            "id": 2,
            "name": "design",
            "color": "#808080"
        }
    ],
    "id": 1,
    "project": 1,
    "title": "Draft the sitemap",
    "description": "",
    "created_at": "2026-09-28T10:45:47.345Z"
}
```

Add two more: `{"title": "Fix broken footer links", "assignee_id": 2, "label_ids": [1, 2]}`, and `{"title": "Pick a color palette"}` with neither field. The last one comes back with `"assignee": null` and `"labels": []`. Bob has no full name, so his `display_name` is `"bob"`.

Bad ids get a `400`. `{"title": "Ghost", "assignee_id": 42}` returns:

```json
{
    "detail": "User 42 does not exist"
}
```

To see the label check, create a second project, `{"name": "Mobile app", "description": "iOS and Android"}`, and give it a label, `{"name": "ios"}`. That label gets id 3. Back on project 1, `{"title": "Wrong label", "label_ids": [3]}` returns:

```json
{
    "detail": "Unknown label id for this project"
}
```

**Go deeper:** [Errors & Exception Handling](../guide/errors.md#throwing-http-errors)

## Computed project fields

A project list is more useful with a count of tasks next to each project. You could compute that in a resolver with `project.tasks.count()`, but that runs one query per project. Let the database compute it for the whole list with `annotate()`:

```python title="projects/api.py" hl_lines="11-15 20 26 31 36 49-52"
from django.db.models import Count, Q
from django.shortcuts import get_object_or_404
from ninja import Router, Status

from .models import Project
from .schemas import LabelIn, LabelOut, ProjectIn, ProjectOut

router = Router(tags=["projects"])


def projects_with_counts():
    return Project.objects.annotate(
        task_count=Count("tasks"),
        unassigned_task_count=Count("tasks", filter=Q(tasks__assignee=None)),
    ).prefetch_related("labels")


@router.get("/", response=list[ProjectOut])
def list_projects(request):
    return projects_with_counts().order_by("id")


@router.post("/", response={201: ProjectOut})
def create_project(request, payload: ProjectIn):
    project = Project.objects.create(**payload.dict())
    return Status(201, projects_with_counts().get(id=project.id))


@router.get("/{project_id}", response=ProjectOut)
def get_project(request, project_id: int):
    return get_object_or_404(projects_with_counts(), id=project_id)


@router.put("/{project_id}", response=ProjectOut)
def update_project(request, project_id: int, payload: ProjectIn):
    project = get_object_or_404(projects_with_counts(), id=project_id)
    for attr, value in payload.dict().items():
        setattr(project, attr, value)
    project.save()
    return project


@router.delete("/{project_id}", response={204: None})
def delete_project(request, project_id: int):
    get_object_or_404(Project, id=project_id).delete()
    return Status(204, None)


@router.post("/{project_id}/labels", response={201: LabelOut})
def create_label(request, project_id: int, payload: LabelIn):
    project = get_object_or_404(Project, id=project_id)
    return Status(201, project.labels.create(**payload.dict()))
```

- An annotation becomes an attribute on each instance, so `ProjectOut` reads `task_count` and `unassigned_task_count` like any other field. The schema doesn't need to know they came from `annotate()`.
- `labels: list[LabelOut]` on `ProjectOut` reads the reverse relation `project.labels`. `ModelSchema` never includes reverse relations on its own, so you declare them yourself.
- Every view that returns a `ProjectOut` gets its project from `projects_with_counts()`. `create_project` fetches the new project again for that reason, and `update_project` keeps the annotated instance it loaded.
- `create_label` creates the label through `project.labels`, which sets its `project` for you.

If a view returns a plain `Project`, you don't get a silent `0`. The response fails validation with `Field required` for `task_count` and `unassigned_task_count`, and the client gets a server error. It's easy to spot in development.

`GET /api/projects/1`, with the three tasks from above:

```json
{
    "labels": [
        {
            "id": 1,
            "name": "bug",
            "color": "#d73a4a"
        },
        {
            "id": 2,
            "name": "design",
            "color": "#808080"
        }
    ],
    "task_count": 3,
    "unassigned_task_count": 1,
    "id": 1,
    "name": "Website redesign",
    "description": "New marketing site",
    "created_at": "2026-09-28T10:45:47.335Z"
}
```

**Go deeper:** [Schemas](../guide/schemas.md#resolvers), [ModelSchema](../guide/model-schema.md#edge-cases-tips)

## Counting queries

Nested output is convenient, but each nested object comes from somewhere. In Part 1, `list_tasks` returned `project.tasks.order_by("id")`. With the new `TaskOut`, every task in that list costs one extra query for its assignee and one for its labels. This is the N+1 problem.

To see it, temporarily change the last line of `list_tasks` back to Part 1's `return project.tasks.order_by("id")`. Then count the queries from the shell. `ninja.testing.TestClient` calls the API directly, without a running server. Part 7 uses it for the test suite.

```console
$ python manage.py shell
>>> from django.db import connection
>>> from django.test.utils import CaptureQueriesContext
>>> from ninja.testing import TestClient
>>> from taskflow.api import api
>>> client = TestClient(api)
>>> with CaptureQueriesContext(connection) as ctx:
...     response = client.get("/projects/1/tasks/")
...
>>> len(ctx.captured_queries)
7
```

That's 7 queries for three tasks with Part 1's queryset: one for the project, one for the tasks, two for the assignees (the third task has none), and three for the labels. Every extra task adds up to two more, so ten tasks take 21 or 22. The fix is to fetch the related rows up front, which is the version of `list_tasks` you typed earlier:

```python title="tasks/api.py"
@router.get("/", response=list[TaskOut])
def list_tasks(request, project_id: Path[int]):
    project = get_object_or_404(Project, id=project_id)
    return project.tasks.select_related("assignee").prefetch_related("labels").order_by("id")
```

- `select_related("assignee")` joins the user table into the tasks query. Use it for foreign keys.
- `prefetch_related("labels")` loads the labels of all the listed tasks in one extra query. Use it for many-to-many and reverse relations.

Restore that line, open a new shell, and run the same code again:

```console
>>> len(ctx.captured_queries)
3
```

It's 3 queries, for three tasks or ten: the project, the tasks joined with their assignees, and the labels. The projects list works the same way. `projects_with_counts()` computes both counts in the main query and adds `.prefetch_related("labels")`, so `GET /api/projects/` takes 2 queries however many projects there are.

!!! tip
    A single `get_task` response has no N+1 problem, so it uses a plain `get_object_or_404`. Optimize the lists first. They're where the query count grows with the data.

**Go deeper:** [Schemas](../guide/schemas.md#nested-schemas-and-lists), [Responses](../guide/responses.md#returning-querysets)

## Recap

- Declare a related field with another schema as its type (`assignee: UserOut | None`, `labels: list[LabelOut]`) to nest it in the output. Related managers are turned into lists for you.
- Accept plain ids on input (`assignee_id`, `label_ids`), check them, and set many-to-many relations after `create()`.
- A `@staticmethod` named `resolve_<field>` computes a field in Python. An `annotate()` in the queryset computes it in the database, and the schema reads it like any other attribute.
- Reverse relations such as `project.labels` are never generated by `ModelSchema`. Declare them on the schema.
- Nested output can cause N+1 queries. Use `select_related` for foreign keys and `prefetch_related` for many-to-many and reverse relations, and count queries with `CaptureQueriesContext`.

## Next

Tasks still have no status, and nothing stops a client from sending a blank title. In [Part 3: Validation & workflows](part-3.md), you'll add status and priority choices, field and model validators, and a status transition endpoint.
