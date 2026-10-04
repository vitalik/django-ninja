# Part 3: Validation & workflows

So far, TaskFlow accepts almost anything a client sends: a title made of spaces is a valid task, and there's no way to say a task is finished. In this part you'll give tasks a status, a priority and a due date, validate input with field and model validators, add a `PATCH` endpoint for partial updates, and move tasks through a small workflow that rejects invalid status changes.

!!! abstract "What you'll learn"
    - How Django `choices` become enums in your schemas and in OpenAPI
    - How to write field validators and model validators, with your own error messages
    - What a `422` validation error looks like, and how to read it
    - How to accept partial updates with `PatchDict`, and what it changes about validation
    - How to reject an invalid state change with `HttpError`

    **Time:** about 15 minutes

## Status, priority and due date

Status and priority are fixed sets of values, so they're Django choices. The allowed status changes go right next to them:

```python title="tasks/models.py" hl_lines="7-27 34-36"
from django.conf import settings
from django.db import models

from projects.models import Label, Project


class TaskStatus(models.TextChoices):
    TODO = "todo"
    IN_PROGRESS = "in_progress"
    DONE = "done"


class Priority(models.IntegerChoices):
    """1 = low, 2 = medium, 3 = high, 4 = urgent"""

    LOW = 1
    MEDIUM = 2
    HIGH = 3
    URGENT = 4


# The statuses a task may move to from each status
ALLOWED_TRANSITIONS = {
    TaskStatus.TODO: {TaskStatus.IN_PROGRESS},
    TaskStatus.IN_PROGRESS: {TaskStatus.TODO, TaskStatus.DONE},
    TaskStatus.DONE: {TaskStatus.IN_PROGRESS},
}


class Task(models.Model):
    project = models.ForeignKey(Project, related_name="tasks", on_delete=models.CASCADE)
    title = models.CharField(max_length=200)
    description = models.TextField(default="")
    status = models.CharField(max_length=20, choices=TaskStatus, default=TaskStatus.TODO)
    priority = models.IntegerField(choices=Priority, default=Priority.MEDIUM)
    due_date = models.DateField(null=True, blank=True)
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

- Priority is an integer, so that "most urgent first" is a plain `order_by("-priority")` later on.
- `ALLOWED_TRANSITIONS` is the whole workflow: from `todo` you can only start a task, and a `done` task can only be reopened as `in_progress`. You'll use it in [Status transitions](#status-transitions).

```console
$ python manage.py makemigrations
Migrations for 'tasks':
  tasks/migrations/0003_task_due_date_task_priority_task_status.py
    + Add field due_date to task
    + Add field priority to task
    + Add field status to task
$ python manage.py migrate
```

The tasks you created in Part 2 get the model defaults. `GET /api/projects/1/tasks/1` now includes the new fields:

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
    "status": "todo",
    "priority": 2,
    "id": 1,
    "project": 1,
    "title": "Draft the sitemap",
    "description": "",
    "due_date": null,
    "created_at": "2026-09-28T10:53:40.574Z"
}
```

## Validating input

`ModelSchema` doesn't look at `choices`: a `status` field from `Meta.fields` is just a `str`, and `priority` is just an `int`. To have the schema accept only valid values, declare the field with the choices class as its type. `TextChoices` and `IntegerChoices` are Python enums, which Pydantic validates and OpenAPI describes.

The rest of the rules go into validators. Here's the new `tasks/schemas.py`:

```python title="tasks/schemas.py" hl_lines="2-4 8 24 28 30-43 50-54 57-58 64-65"
from django.contrib.auth.models import User
from ninja import ModelSchema, Schema
from pydantic import field_validator, model_validator
from pydantic_core import PydanticCustomError

from projects.schemas import LabelOut

from .models import Priority, Task, TaskStatus


class UserOut(ModelSchema):
    display_name: str

    class Meta:
        model = User
        fields = ["id", "username"]

    @staticmethod
    def resolve_display_name(user):
        return user.get_full_name() or user.username


class TaskUpdate(ModelSchema):
    priority: Priority = Priority.MEDIUM

    class Meta:
        model = Task
        fields = ["title", "description", "priority", "due_date"]

    @field_validator("title", "description", "priority", check_fields=False)
    @classmethod
    def not_null(cls, value):
        if value is None:
            raise PydanticCustomError("not_null", "This field can't be null")
        return value

    @field_validator("title", check_fields=False)
    @classmethod
    def title_not_blank(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise PydanticCustomError("blank", "Title can't be blank")
        return value


class TaskIn(TaskUpdate):
    assignee_id: int | None = None
    label_ids: list[int] = []

    @model_validator(mode="after")
    def urgent_needs_due_date(self):
        if self.priority == Priority.URGENT and self.due_date is None:
            raise ValueError("Urgent tasks need a due date")
        return self


class StatusIn(Schema):
    status: TaskStatus


class TaskOut(ModelSchema):
    assignee: UserOut | None
    labels: list[LabelOut]
    status: TaskStatus
    priority: Priority

    class Meta:
        model = Task
        fields = ["id", "project", "title", "description", "due_date", "created_at"]
```

- `TaskUpdate` holds the fields a client can edit: title, description, priority and due date. `TaskIn` extends it with the fields you only set on create. A `ModelSchema` subclass inherits `Meta`, fields and validators, so `TaskIn` has everything `TaskUpdate` has.
- `status` isn't in either input schema. New tasks always start as `todo`, and the only way to change the status is the transition endpoint below.
- `title_not_blank` is a **field validator**. It runs after the type check, gets the value, and returns what should be stored, here the stripped title.
- `not_null` does nothing on a normal request, because the type check already rejects `null` for these fields. It exists for the `PATCH` endpoint, explained in the next section.
- `urgent_needs_due_date` is a **model validator**. With `mode="after"` it runs once every field is valid, so it can compare fields. It returns `self`.
- `StatusIn` is the body of the transition endpoint. `TaskOut` declares `status` and `priority` with their enums so the response schema lists the allowed values too.

!!! note "Why `check_fields=False`?"
    Pydantic checks that a validator's field names exist when the class is created. `ModelSchema` adds the `Meta.fields` afterwards, so without `check_fields=False` a validator for `title` fails with `PydanticUserError: Decorators defined with incorrect fields`. Fields you declare yourself, such as `priority`, don't need it.

### Error messages

A validator reports a problem by raising an exception, and Django Ninja turns it into a `422` response. What the client sees depends on what you raise:

- `ValueError("...")` gives the type `value_error`, and Pydantic adds `Value error, ` before your message.
- `PydanticCustomError(type, message)` uses your type and your message exactly as written. Clients can match on the type.

### Try it

`POST /api/projects/1/tasks/` with `{"title": "  Write launch announcement ", "priority": 3, "due_date": "2026-10-15"}` returns `201`, with the title stripped:

```json
{
    "assignee": null,
    "labels": [],
    "status": "todo",
    "priority": 3,
    "id": 4,
    "project": 1,
    "title": "Write launch announcement",
    "description": "",
    "due_date": "2026-10-15",
    "created_at": "2026-09-28T10:53:40.592Z"
}
```

Invalid input gets a `422` with a list of errors. When several fields are wrong, you get all of them in one response. `{"title": "", "priority": 5, "due_date": "next friday"}` returns:

```json
{
    "detail": [
        {
            "type": "enum",
            "loc": [
                "body",
                "payload",
                "priority"
            ],
            "msg": "Input should be 1, 2, 3 or 4",
            "ctx": {
                "expected": "1, 2, 3 or 4"
            }
        },
        {
            "type": "blank",
            "loc": [
                "body",
                "payload",
                "title"
            ],
            "msg": "Title can't be blank"
        },
        {
            "type": "date_from_datetime_parsing",
            "loc": [
                "body",
                "payload",
                "due_date"
            ],
            "msg": "Input should be a valid date or datetime, invalid character in year",
            "ctx": {
                "error": "invalid character in year"
            }
        }
    ]
}
```

`loc` is the path to each bad value: the request body, the view argument `payload`, then the field. `type` and `msg` of the title error come from the `PydanticCustomError` in `title_not_blank`.

The model validator runs only when every field is valid. `{"title": "Fix checkout bug", "priority": 4}` has no due date, so it gets an error for the whole payload, with the `Value error, ` prefix that comes from `ValueError`:

```json
{
    "detail": [
        {
            "type": "value_error",
            "loc": [
                "body",
                "payload"
            ],
            "msg": "Value error, Urgent tasks need a due date",
            "ctx": {
                "error": "Urgent tasks need a due date"
            }
        }
    ]
}
```

None of these requests reach the view, so nothing is saved.

In the interactive docs at `/api/docs`, the schemas now include both enums. `Priority` uses the class docstring as its description, which is the easiest way to explain what the numbers mean:

```json
{
    "description": "1 = low, 2 = medium, 3 = high, 4 = urgent",
    "enum": [
        1,
        2,
        3,
        4
    ],
    "title": "Priority",
    "type": "integer"
}
```

**Go deeper:** [Schemas](../guide/schemas.md#schema-vs-plain-pydantic-models), [Errors & Exception Handling](../guide/errors.md#customizing-validation-errors)

## Partial updates with PATCH

Part 1's `PUT` for projects replaces every field. For tasks, a client usually changes one thing at a time, such as the priority. That's a `PATCH`, and `PatchDict` handles it. Here's the full `tasks/api.py` with the two new endpoints:

```python title="tasks/api.py" hl_lines="3 8-9 43-61"
from django.contrib.auth.models import User
from django.shortcuts import get_object_or_404
from ninja import PatchDict, Path, Router, Status
from ninja.errors import HttpError

from projects.models import Project

from .models import ALLOWED_TRANSITIONS, Priority, Task
from .schemas import StatusIn, TaskIn, TaskOut, TaskUpdate

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


@router.patch("/{task_id}", response=TaskOut)
def update_task(request, project_id: Path[int], task_id: int, payload: PatchDict[TaskUpdate]):
    task = get_object_or_404(Task, id=task_id, project_id=project_id)
    for attr, value in payload.items():
        setattr(task, attr, value)
    if task.priority == Priority.URGENT and task.due_date is None:
        raise HttpError(400, "Urgent tasks need a due date")
    task.save()
    return task


@router.post("/{task_id}/status", response=TaskOut)
def change_status(request, project_id: Path[int], task_id: int, payload: StatusIn):
    task = get_object_or_404(Task, id=task_id, project_id=project_id)
    if payload.status not in ALLOWED_TRANSITIONS[task.status]:
        raise HttpError(409, f"Can't move a task from {task.status} to {payload.status}")
    task.status = payload.status
    task.save()
    return task
```

- `PatchDict[TaskUpdate]` makes every field of `TaskUpdate` optional and gives the view a plain `dict` with only the keys the client sent. The loop copies those onto the task and leaves the rest alone.
- The field validators still run on the values that were sent, so a blank title is rejected on `PATCH` as well.
- `create_task` didn't change. `payload.dict()` now includes `priority` and `due_date`, and `Task.objects.create()` accepts them as they are.

`PatchDict` makes every field optional by also allowing `null`. For `due_date`, `null` is useful: it clears the date. For `title`, `description` and `priority`, the database column can't hold `NULL`, and a `null` would reach `task.save()` and fail with an `IntegrityError`. The `not_null` validator stops it first. `PATCH /api/projects/1/tasks/4` with `{"title": null}` returns:

```json
{
    "detail": [
        {
            "type": "not_null",
            "loc": [
                "body",
                "payload",
                "title"
            ],
            "msg": "This field can't be null"
        }
    ]
}
```

### Rules that need the stored data

`PATCH` uses `TaskUpdate`, not `TaskIn`, so the urgent rule doesn't run as a model validator there. It couldn't work on a partial payload anyway: a validator only sees the request body, and `{"priority": 4}` doesn't include the due date the task already has. So `update_task` checks the rule on the task itself, after the changes are applied and before anything is saved.

Task 4 has a due date, so `PATCH /api/projects/1/tasks/4` with `{"priority": 4}` returns `200` with `"priority": 4`, and the title and due date unchanged.

Clearing the due date of that urgent task with `{"due_date": null}` returns `400`, and the task keeps its date:

```json
{
    "detail": "Urgent tasks need a due date"
}
```

This error comes from `HttpError`, so it has the simple `{"detail": "..."}` shape rather than a list. Use validators for what the request alone can decide, and checks in the view for anything that depends on the database.

**Go deeper:** [Request Body](../guide/body.md#partial-updates-with-patchdict), [ModelSchema](../guide/model-schema.md#patchdict)

## Status transitions

A status isn't just another field to `PATCH`. Whether `done` is a valid new status depends on the current one. That's why status has its own endpoint, `POST /api/projects/{project_id}/tasks/{task_id}/status`:

```python title="tasks/api.py"
@router.post("/{task_id}/status", response=TaskOut)
def change_status(request, project_id: Path[int], task_id: int, payload: StatusIn):
    task = get_object_or_404(Task, id=task_id, project_id=project_id)
    if payload.status not in ALLOWED_TRANSITIONS[task.status]:
        raise HttpError(409, f"Can't move a task from {task.status} to {payload.status}")
    task.status = payload.status
    task.save()
    return task
```

- `StatusIn` makes sure the value is one of the three statuses. The view only has to decide whether this change is allowed.
- `ALLOWED_TRANSITIONS[task.status]` is the set of statuses the task can move to. `task.status` is a plain string when it's loaded from the database, and it still finds the `TaskStatus` key, because a `TextChoices` member compares and hashes like its string value.
- `409 Conflict` says the request was well formed but clashes with the current state of the task. The message tells the client which move was refused.

Task 4 is still `todo`, so `{"status": "done"}` is refused:

```json
{
    "detail": "Can't move a task from todo to done"
}
```

Starting it first with `{"status": "in_progress"}` returns `200` and the task with `"status": "in_progress"`. After that, `{"status": "done"}` works. A status that doesn't exist never reaches the view. `{"status": "archived"}` returns a `422` from the enum:

```json
{
    "detail": [
        {
            "type": "enum",
            "loc": [
                "body",
                "payload",
                "status"
            ],
            "msg": "Input should be 'todo', 'in_progress' or 'done'",
            "ctx": {
                "expected": "'todo', 'in_progress' or 'done'"
            }
        }
    ]
}
```

**Go deeper:** [Errors & Exception Handling](../guide/errors.md#throwing-http-errors)

## Recap

- Declare `TextChoices` and `IntegerChoices` fields with the choices class as their type. The schema then accepts only valid values, and OpenAPI lists them.
- A `@field_validator` checks and cleans one field. A `@model_validator(mode="after")` compares fields once they're all valid. Validators on `Meta.fields` need `check_fields=False`.
- Raise `PydanticCustomError` for your own error type and message, or `ValueError` for a quick `value_error`. Either way the client gets a `422` with every problem listed.
- `PatchDict[Schema]` gives the view a dict of only the fields sent. It also accepts `null` for every field, so reject it where the column can't be empty.
- Validators only see the request. Check rules that depend on stored data, such as allowed status changes, in the view and raise `HttpError`.

## Next

Anyone can still read and change every project. In [Part 4: Auth & permissions](part-4.md), you'll add JWT authentication, project memberships with roles, and comments that only their author can edit.
