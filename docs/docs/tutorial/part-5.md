# Part 5: Filtering, search, ordering & pagination

`GET /api/projects/{project_id}/tasks/` returns every task of a project in one response. That's fine for a handful, but a real team wants the tasks assigned to them, the overdue ones, or the ones mentioning "checkout", and it doesn't want a thousand of them at once. In this part you'll add filters and search with a `FilterSchema`, let clients pick the sort order from a fixed list, and paginate tasks by page number and comments with a cursor.

!!! abstract "What you'll learn"
    - How to turn query parameters into ORM lookups with `FilterSchema` and `FilterLookup`
    - How to search several fields at once, and accept a list of values for one parameter
    - How to restrict an `ordering` parameter to a fixed set of values with `Literal`
    - How to paginate a list with `@paginate` and `PageNumberPagination`
    - How cursor pagination works, and when to prefer it

    **Time:** about 15 minutes

## Some tasks to work with

Filters are more interesting with more than four tasks. Add three to the "Website redesign" project, plus a few comments on task 2. Django's shell imports your models automatically:

```console
$ python manage.py shell
>>> fix = Task.objects.create(
...     project_id=1, title="Fix mobile menu overlap", assignee_id=2, priority=4,
...     due_date="2026-10-01", description="The menu covers the logo on small screens",
... )
>>> fix.labels.add(1)
>>> Task.objects.create(project_id=1, title="Set up analytics", description="Page views and the signup funnel", due_date="2026-10-20")
<Task: Set up analytics>
>>> Task.objects.create(project_id=1, title="Compress hero images", assignee_id=2, priority=3, due_date="2026-10-03")
<Task: Compress hero images>
>>> for body in ["Found three more on the pricing page.", "Fixed on staging.", "Looks good, closing."]:
...     Comment.objects.create(task_id=2, author_id=2, body=body)
...
<Comment: Comment by bob on Fix broken footer links>
<Comment: Comment by bob on Fix broken footer links>
<Comment: Comment by bob on Fix broken footer links>
```

The project now has seven tasks: 1 to 4 from the earlier parts and the new 5, 6 and 7. Task 2 has four comments, with ids 2 to 5. Nothing in this part changes a model, so there are no migrations.

## A filter schema

A `FilterSchema` is a `Schema` whose fields are query parameters, with a `.filter()` method that turns them into a `Q` expression. Add one to `tasks/schemas.py`, together with the list of allowed sort orders:

```python title="tasks/schemas.py" hl_lines="1-2 4 16-23 26-28"
from datetime import date
from typing import Annotated, Literal

from ninja import FilterLookup, FilterSchema, ModelSchema, Schema
from pydantic import field_validator, model_validator
from pydantic_core import PydanticCustomError

from accounts.schemas import UserOut
from projects.schemas import LabelOut

from .models import Comment, Priority, Task, TaskStatus

...


class TaskFilter(FilterSchema):
    status: Annotated[list[TaskStatus] | None, FilterLookup("status__in")] = None
    assignee: Annotated[str | None, FilterLookup("assignee__username")] = None
    label: Annotated[str | None, FilterLookup("labels__name")] = None
    due_before: Annotated[date | None, FilterLookup("due_date__lt")] = None
    search: Annotated[
        str | None, FilterLookup(["title__icontains", "description__icontains"])
    ] = None


TaskOrdering = Literal[
    "created_at", "-created_at", "due_date", "-due_date", "priority", "-priority"
]
```

- Every field defaults to `None`, and a `None` field is skipped. A request without query parameters is not filtered at all.
- `FilterLookup` sets the ORM lookup for a field. Without it, the field name is used, as in `Q(status=value)`. The public parameter names stay short (`assignee`, `label`), while the lookups follow relations (`assignee__username`, `labels__name`).
- `status` is a list, so a client can repeat the parameter: `?status=todo&status=in_progress` becomes `Q(status__in=[...])`. The items are `TaskStatus` values, so an unknown status is a `422`.
- `search` has a list of lookups. They're combined with `OR`, so the term can appear in the title or the description. The different fields are combined with `AND`.
- `due_before` is a `date`, parsed and validated like any other schema field.
- `TaskOrdering` is used in the view below.

**Go deeper:** [Filtering: custom lookups](../guide/filtering.md#custom-lookups-with-filterlookup), [Filtering: combining expressions](../guide/filtering.md#combining-expressions)

## Filters, ordering and pages in the view

Here's the new `list_tasks`, with the imports it needs:

```python title="tasks/api.py" hl_lines="2 4 14 16 25 29-30 33-34"
from django.shortcuts import get_object_or_404
from ninja import PatchDict, Path, Query, Router, Status
from ninja.errors import HttpError
from ninja.pagination import CursorPagination, PageNumberPagination, paginate

from projects.models import Role
from projects.permissions import get_project_or_404

from .models import ALLOWED_TRANSITIONS, Priority, Task
from .schemas import (
    CommentIn,
    CommentOut,
    StatusIn,
    TaskFilter,
    TaskIn,
    TaskOrdering,
    TaskOut,
    TaskUpdate,
)

...


@router.get("/", response=list[TaskOut])
@paginate(PageNumberPagination, page_size=20)
def list_tasks(
    request,
    project_id: Path[int],
    filters: Query[TaskFilter],
    ordering: TaskOrdering = "created_at",
):
    project = get_project_or_404(request.auth, project_id)
    tasks = filters.filter(project.tasks.select_related("assignee").prefetch_related("labels"))
    return tasks.order_by(ordering, "id")
```

- `Query[TaskFilter]` reads the schema's fields from the query string, so the parameters are `?status=...&search=...`, not `?filters=...`.
- `filters.filter()` applies the filters to the queryset it's given. That queryset is already scoped to a project the user belongs to, so the filters can only narrow Part 4's permissions, never widen them.
- `ordering` is a plain query parameter typed with the `Literal`. Only the six listed values get through, which matters because the value goes straight into `order_by()`. Never pass a client's string to `order_by()` unchecked. It would let them sort by any field, including ones they can't see, such as a related user's password hash.
- `"id"` comes second in `order_by()`, so tasks with the same priority or due date always come back in the same order. Stable ordering matters once results are split into pages.
- `@paginate` goes below the router decorator. The view still returns a queryset, and `response` still says `list[TaskOut]`. The next section covers what it changes.

### Try it

The shell is quicker than curl for a series of queries. `TestClient` from Part 2 can send the token as a default header. With a small helper that prints only the titles:

```console
$ python manage.py shell
>>> from accounts.tokens import create_token_pair
>>> from ninja.testing import TestClient
>>> from taskflow.api import api
>>> token = create_token_pair(1)["access"]
>>> client = TestClient(api, headers={"Authorization": f"Bearer {token}"})
>>> def titles(query):
...     return [task["title"] for task in client.get(f"/projects/1/tasks/?{query}").json()["items"]]
...
>>> titles("assignee=bob")
['Fix broken footer links', 'Fix mobile menu overlap', 'Compress hero images']
>>> titles("status=in_progress&status=done")
['Write launch announcement']
>>> titles("label=bug")
['Fix broken footer links', 'Fix mobile menu overlap']
>>> titles("search=fix")
['Fix broken footer links', 'Fix mobile menu overlap']
>>> titles("search=SIGNUP")
['Set up analytics']
>>> titles("due_before=2026-10-10&ordering=due_date")
['Fix mobile menu overlap', 'Compress hero images']
>>> titles("status=todo&ordering=-priority")
['Fix mobile menu overlap', 'Compress hero images', 'Draft the sitemap', 'Fix broken footer links', 'Pick a color palette', 'Set up analytics']
```

- `search=SIGNUP` finds "Set up analytics" through its description, because `icontains` ignores case.
- Filtering on `label=bug` only selects the tasks. Their `labels` in the response still list every label, because `prefetch_related` loads them in a separate query.
- With `-priority`, the four tasks with priority 2 come out in `id` order, thanks to the second `order_by()` field.
- On SQLite, tasks without a due date come first with `ordering=due_date`. PostgreSQL puts them last. Combine the ordering with `due_before`, as above, to leave them out.

Values that don't fit the types are rejected before the view runs. `?ordering=oldest` returns a `422`:

```json
{
    "detail": [
        {
            "type": "literal_error",
            "loc": [
                "query",
                "ordering"
            ],
            "msg": "Input should be 'created_at', '-created_at', 'due_date', '-due_date', 'priority' or '-priority'",
            "ctx": {
                "expected": "'created_at', '-created_at', 'due_date', '-due_date', 'priority' or '-priority'"
            }
        }
    ]
}
```

And `?status=archived` fails on the first list item. The `loc` includes `filters`, the name of the view parameter that holds the schema:

```json
{
    "detail": [
        {
            "type": "enum",
            "loc": [
                "query",
                "filters",
                "status",
                0
            ],
            "msg": "Input should be 'todo', 'in_progress' or 'done'",
            "ctx": {
                "expected": "'todo', 'in_progress' or 'done'"
            }
        }
    ]
}
```

In the interactive docs, each filter shows up as its own query parameter, and `ordering` as a dropdown with the six values.

**Go deeper:** [Filtering](../guide/filtering.md#basic-usage), [Query Parameters](../guide/query-params.md#multiple-values-lists)

## Page numbers

`@paginate(PageNumberPagination, page_size=20)` adds two query parameters, `page` (starting at 1) and `page_size`, and wraps the result in an object with the page's `items` and the total `count`. The shell helper above already read `["items"]`. With `TOKEN` set as in Part 4 (access tokens expire after 15 minutes, so get a fresh one from `POST /api/auth/token` if you get a `401`), ask for the third page of three tasks, sorted by priority:

```console
$ curl "http://127.0.0.1:8000/api/projects/1/tasks/?ordering=-priority&page=3&page_size=3" -H "Authorization: Bearer $TOKEN"
```

```json
{
    "items": [
        {
            "assignee": null,
            "labels": [],
            "status": "todo",
            "priority": 2,
            "id": 6,
            "project": 1,
            "title": "Set up analytics",
            "description": "Page views and the signup funnel",
            "due_date": "2026-10-20",
            "created_at": "2026-09-28T11:08:55.867Z"
        }
    ],
    "count": 7
}
```

- The paginator slices the queryset, so the database only returns the rows of the requested page. `count` is one extra `COUNT` query with the same filters. The filtered, paginated list takes 5 queries in total: the user from the token, the membership, the count, the tasks with their assignees, and the labels.
- Without `page_size`, a page has 20 tasks. A client can ask for more, up to `max_page_size`, which defaults to 100. `?page_size=500` returns at most 100 tasks.
- A page past the end, such as `?page=9`, is not an error. It returns `{"items": [], "count": 7}`. `?page=0` is a `422`, because `page` must be at least 1.
- In the OpenAPI schema, the response is now `PagedTaskOut`, with `items` and `count`. Django Ninja generates it from `list[TaskOut]`.

Page numbers are what most UIs need: "page 3 of 5", with a total. Their weak point is data that changes while someone is paging. If a task is added at the top between two requests, every page shifts by one, and the client sees one task twice.

**Go deeper:** [Pagination](../guide/pagination.md#pagenumberpagination)

## Cursor pagination for comments

Comments grow at the end, and clients load them as a feed, "show more" by "show more". That's what `CursorPagination` is for. Instead of a page number, each response has a `next` link that points just past the last item seen. In `tasks/api.py`, add the decorator to `list_comments` and drop the `.order_by("id")`:

```python title="tasks/api.py" hl_lines="2 5"
@router.get("/{task_id}/comments", response=list[CommentOut])
@paginate(CursorPagination, ordering=("id",), page_size=20)
def list_comments(request, project_id: Path[int], task_id: int):
    task = get_task_or_404(request.auth, project_id, task_id)
    return task.comments.select_related("author")
```

- `ordering` belongs to the paginator now. It sorts the queryset itself, and uses the first field to record the position in the cursor. That field should be unique, or close to it. The comment id is unique and grows with time, so the oldest comments come first.
- The parameters are `cursor` and `page_size`. There is no page number and no `count`.

Ask for two comments at a time:

```console
$ curl "http://127.0.0.1:8000/api/projects/1/tasks/2/comments?page_size=2" -H "Authorization: Bearer $TOKEN"
```

```json
{
    "previous": null,
    "next": "http://127.0.0.1:8000/api/projects/1/tasks/2/comments?cursor=cD00&page_size=2",
    "results": [
        {
            "author": {
                "display_name": "Alice Martin",
                "id": 1,
                "username": "alice"
            },
            "id": 2,
            "body": "Good catch, thanks!",
            "created_at": "2026-09-28T11:08:55.863Z"
        },
        {
            "author": {
                "display_name": "bob",
                "id": 2,
                "username": "bob"
            },
            "id": 3,
            "body": "Found three more on the pricing page.",
            "created_at": "2026-09-28T11:08:55.867Z"
        }
    ]
}
```

The items are under `results`, not `items`. The `next` link keeps the other query parameters and adds a cursor. `cD00` is base64 for `p=4`: the next page starts at comment id 4. Follow the link:

```json
{
    "previous": "http://127.0.0.1:8000/api/projects/1/tasks/2/comments?cursor=cD00JnI9VHJ1ZSZvPTE%3D&page_size=2",
    "next": null,
    "results": [
        {
            "author": {
                "display_name": "bob",
                "id": 2,
                "username": "bob"
            },
            "id": 4,
            "body": "Fixed on staging.",
            "created_at": "2026-09-28T11:08:55.869Z"
        },
        {
            "author": {
                "display_name": "bob",
                "id": 2,
                "username": "bob"
            },
            "id": 5,
            "body": "Looks good, closing.",
            "created_at": "2026-09-28T11:08:55.870Z"
        }
    ]
}
```

- `next` is `null` on the last page, and `previous` leads back to comments 2 and 3.
- The cursor is a position, not an offset. If someone adds a comment and the client follows the same `next` link again, it still gets comments 4 and 5, now with a `next` link to the new comment. Nothing is skipped or shown twice.
- The paginator fetches one row more than the page size to know whether there's a next page, so it needs no `COUNT` query. That keeps it fast on large tables, but a UI can't show "page 3 of 5".
- The cursor is only encoded, not signed. A client can craft one, but it can only move the position inside the queryset the view returns, which is already limited to the task's comments. A cursor that isn't valid base64 returns a `422` with `{"detail": [{"cursor": "Invalid Cursor"}]}`.

**Go deeper:** [Pagination](../guide/pagination.md#cursorpagination)

## Recap

- A `FilterSchema` declares filters as typed fields, and `filters.filter(queryset)` turns the fields that were sent into a `Q` expression. Use it with `Query[...]`.
- `FilterLookup` maps a short parameter name to any ORM lookup. A list of lookups is combined with `OR`, which is all a simple search needs.
- Accept a sort order only from a `Literal` of allowed values, and add a unique field such as `id` as a tie-breaker.
- `@paginate(PageNumberPagination)` wraps a view that returns a queryset. It slices the query and adds `count`. Clients get page numbers and totals.
- `@paginate(CursorPagination, ordering=...)` gives `next`/`previous` links that stay correct while data is added, without a `COUNT` query. Use it for feeds such as comments.

## Next

Tasks can have comments, but not files. In [Part 6: File uploads & forms](part-6.md), you'll attach files to tasks with multipart uploads, validate their size and type, and return absolute URLs for them.
