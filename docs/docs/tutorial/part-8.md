# Part 8: OpenAPI polish & versioning

TaskFlow works and is tested. Other people will build against it, though, and for them the interactive docs are the API. In this last part you'll make the generated schema say more: what the API is for, what each operation does, and what each field expects. Then you'll ship a breaking change the safe way, as a version 2 that runs next to version 1.

!!! abstract "What you'll learn"
    - How to set the API's title, version and description
    - How summaries, docstrings and `Field(description=..., examples=...)` show up in the schema
    - How to hide an internal endpoint and mark old ones as deprecated
    - How to run two `NinjaAPI` versions side by side, sharing the routers that didn't change
    - How URL namespaces keep `reverse()` working with more than one API

    **Time:** about 15 minutes

## Describing the API

Open `taskflow/api.py`. `NinjaAPI` takes a `version` and a `description` next to the `title` you set in Part 1:

```python title="taskflow/api.py" hl_lines="5-8 10"
from ninja import NinjaAPI

from accounts.auth import JWTAuth

DESCRIPTION = (
    "Track the tasks of your team's projects: members, labels, comments and attachments.\n\n"
    "Get a token from `POST /auth/token`, then click **Authorize** and paste it."
)

api = NinjaAPI(title="TaskFlow API", version="1.0", description=DESCRIPTION, auth=JWTAuth())
...
```

Leave the `add_router()` calls below it as they are for now. You'll see the complete file once [version 2](#a-second-version) is in place.

The three values end up in the `info` block of `/api/openapi.json`:

```json
{
    "title": "TaskFlow API",
    "version": "1.0",
    "description": "Track the tasks of your team's projects: members, labels, comments and attachments.\n\nGet a token from `POST /auth/token`, then click **Authorize** and paste it."
}
```

- The docs page shows the title with the version next to it, and renders the description as Markdown, so `**Authorize**` comes out bold.
- `version` is a plain string. Django Ninja doesn't parse it, but it does use it for the URL namespace, as you'll see at the end of this page.

**Go deeper:** [The NinjaAPI Instance](../guide/api.md#title-version-and-description)

## Summaries and descriptions

Every operation gets a summary, the one-line name in the docs. By default it's the function name in title case: `list_tasks` becomes "List Tasks", and `create_task` becomes "Create Task". Good function names already give good summaries. When they don't, pass `summary=`. A docstring becomes the operation's description:

```python title="tasks/api.py" hl_lines="9 18 20-28"
@router.get("/", response=list[TaskOut])
@paginate(PageNumberPagination, page_size=20)
def list_tasks(
    request,
    project_id: Path[int],
    filters: Query[TaskFilter],
    ordering: TaskOrdering = "created_at",
):
    """List the tasks of a project, 20 per page. Filters combine with AND."""
    project = get_project_or_404(request.auth, project_id)
    tasks = filters.filter(project.tasks.select_related("assignee").prefetch_related("labels"))
    return tasks.order_by(ordering, "id")


...


@router.post("/{task_id}/status", response=TaskOut, summary="Move a task to another status")
def change_status(request, project_id: Path[int], task_id: int, payload: StatusIn):
    """
    Allowed moves:

    - `todo` to `in_progress`
    - `in_progress` to `todo` or `done`
    - `done` to `in_progress`

    Any other move returns **409 Conflict**.
    """
    task = get_task_or_404(request.auth, project_id, task_id)
    if payload.status not in ALLOWED_TRANSITIONS[task.status]:
        raise HttpError(409, f"Can't move a task from {task.status} to {payload.status}")
    task.status = payload.status
    task.save()
    return task
```

"Change Status" would be a fine summary too, but it doesn't say what it changes. Here is the operation in `/api/openapi.json`, with the parameters and responses left out:

```json
{
    "operationId": "tasks_api_change_status",
    "summary": "Move a task to another status",
    "description": "Allowed moves:\n\n- `todo` to `in_progress`\n- `in_progress` to `todo` or `done`\n- `done` to `in_progress`\n\nAny other move returns **409 Conflict**.",
    "tags": [
        "tasks"
    ]
}
```

- The docstring's indentation is removed, and the docs render the list and the bold text as Markdown.
- The docstring is the place for rules a client can't see in the schema, such as the transitions from Part 3. The schema already says that `status` is one of three values. It can't say which moves are allowed.
- `operationId` is built from the module and function name. Client generators typically use it to name the generated method. Pass `operation_id="..."` to an operation to choose your own. It must be unique across the schema.
- `tags` comes from `Router(tags=["tasks"])` in Part 1.

**Go deeper:** [Operations: summary](../guide/operations.md#summary), [Operations: operation_id](../guide/operations.md#operation_id)

## Describing fields

Field names like `title` and `due_date` explain themselves. `assignee_id` and `label_ids` have rules the schema can't show on its own: they must point to a member and to labels of the same project. Pydantic's `Field()` adds a description and example values:

```python title="tasks/schemas.py" hl_lines="2-3 15"
class TaskIn(TaskUpdate):
    assignee_id: int | None = Field(None, description="A member of the project", examples=[2])
    label_ids: list[int] = Field([], description="Labels of the same project", examples=[[1]])

...


class TaskFilter(FilterSchema):
    status: Annotated[list[TaskStatus] | None, FilterLookup("status__in")] = None
    assignee: Annotated[str | None, FilterLookup("assignee__username")] = None
    label: Annotated[str | None, FilterLookup("labels__name")] = None
    due_before: Annotated[date | None, FilterLookup("due_date__lt")] = None
    search: Annotated[
        str | None, FilterLookup(["title__icontains", "description__icontains"])
    ] = Field(None, description="Text to find in the title or the description")
```

The first argument of `Field()` is the default, the same value the fields had before. `Field` is already imported in `tasks/schemas.py` from Part 6. The two fields in the `TaskIn` schema:

```json
{
    "assignee_id": {
        "anyOf": [
            {
                "type": "integer"
            },
            {
                "type": "null"
            }
        ],
        "description": "A member of the project",
        "examples": [
            2
        ],
        "title": "Assignee Id"
    },
    "label_ids": {
        "default": [],
        "description": "Labels of the same project",
        "examples": [
            [
                1
            ]
        ],
        "items": {
            "type": "integer"
        },
        "title": "Label Ids",
        "type": "array"
    }
}
```

- `examples` is a list of complete values. For a list field, each example is itself a list, hence `[[1]]`.
- The same works in a `FilterSchema`. `search` is a query parameter, and its description appears next to it in the docs:

```json
{
    "in": "query",
    "name": "search",
    "schema": {
        "anyOf": [
            {
                "type": "string"
            },
            {
                "type": "null"
            }
        ],
        "description": "Text to find in the title or the description",
        "title": "Search"
    },
    "required": false,
    "description": "Text to find in the title or the description"
}
```

**Go deeper:** [Query Parameters](../guide/query-params.md#validation-constraints), [Request Body](../guide/body.md#automatic-docs-and-editor-support)

## Hiding an internal endpoint

A load balancer or an uptime monitor needs a URL that answers without a token. It's not part of the API you offer to clients, so it doesn't belong in the docs. Register it on `api` directly, with no auth and `include_in_schema=False`:

```python title="taskflow/api.py"
@api.get("/health", auth=None, include_in_schema=False)
def health(request):
    return {"status": "ok"}
```

`GET /api/health` works without a token:

```json
{
    "status": "ok"
}
```

`/api/health` isn't in the `paths` of `/api/openapi.json`, so the docs don't show it. Hiding an operation is not a security measure: anyone who knows the URL can still call it. Protect it with auth if it returns anything private.

**Go deeper:** [Operations: include_in_schema](../guide/operations.md#include_in_schema)

## A second version

A mobile team wants to use TaskFlow with a standard OAuth2 client library. The library expects the token response to use OAuth2's field names: `access_token`, `refresh_token`, `token_type` and `expires_in`. TaskFlow returns `access` and `refresh`. Renaming the fields would break every client that already logs in, so the new shape goes into a version 2 of the API. Version 1 stays as it is.

The new schemas go into `accounts/schemas.py`:

```python title="accounts/schemas.py" hl_lines="1 5 10-18"
from typing import Literal

from django.contrib.auth.models import User
from ninja import ModelSchema, Schema
from pydantic import Field

...


class OAuthTokenOut(Schema):
    access_token: str
    refresh_token: str
    token_type: Literal["bearer"]
    expires_in: int = Field(description="Seconds until the access token expires", examples=[900])


class OAuthRefreshIn(Schema):
    refresh_token: str
```

The version 2 endpoints go into a new module:

```python title="accounts/api_v2.py" hl_lines="3 10-16 22 28"
from ninja import Router

from . import api as v1
from .schemas import OAuthRefreshIn, OAuthTokenOut, RefreshIn, TokenIn
from .tokens import ACCESS_TOKEN_LIFETIME

tokens = Router(tags=["auth"], auth=None)


def oauth_response(pair):
    return {
        "access_token": pair["access"],
        "refresh_token": pair["refresh"],
        "token_type": "bearer",
        "expires_in": ACCESS_TOKEN_LIFETIME,
    }


@tokens.post("/token", response=OAuthTokenOut)
def obtain_token(request, payload: TokenIn):
    """Exchange a username and password for an access and a refresh token."""
    return oauth_response(v1.obtain_token(request, payload))


@tokens.post("/refresh", response=OAuthTokenOut)
def refresh_token(request, payload: OAuthRefreshIn):
    """Exchange a refresh token for a new pair of tokens."""
    return oauth_response(v1.refresh_token(request, RefreshIn(refresh=payload.refresh_token)))
```

- Only the shape changes, so version 2 calls the version 1 views. An operation decorator registers the function and returns it unchanged, so `v1.obtain_token` is still a plain Python function.
- The `HttpError(401, ...)` raised inside a v1 view propagates to the v2 operation and becomes the same `401` response.
- The login request body, `TokenIn`, doesn't change. The refresh body does, from `refresh` to `refresh_token`.

### Splitting the auth router

A router is the unit you mount into an API. You can't mount a router without some of its operations, so everything that differs between versions must live in a router of its own. In `accounts/api.py`, `signup` stays on `router`, and the two token endpoints move to a new `tokens` router that only version 1 mounts:

```python title="accounts/api.py" hl_lines="11-12 27-29 36-38"
from django.contrib.auth import authenticate
from django.contrib.auth.models import User
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError
from ninja import Router, Status
from ninja.errors import HttpError

from .schemas import RefreshIn, SignupIn, TokenIn, TokenOut, UserOut
from .tokens import create_token_pair, decode_token

router = Router(tags=["auth"], auth=None)  # shared by v1 and v2
tokens = Router(tags=["auth"], auth=None)  # v1 only


@router.post("/signup", response={201: UserOut})
def signup(request, payload: SignupIn):
    if User.objects.filter(username=payload.username).exists():
        raise HttpError(409, "This username is taken")
    try:
        validate_password(payload.password)
    except ValidationError as e:
        raise HttpError(400, " ".join(e.messages))
    user = User.objects.create_user(payload.username, password=payload.password)
    return Status(201, user)


@tokens.post("/token", response=TokenOut, deprecated=True)
def obtain_token(request, payload: TokenIn):
    """Use `POST /api/v2/auth/token` instead."""
    user = authenticate(username=payload.username, password=payload.password)
    if user is None:
        raise HttpError(401, "Invalid username or password")
    return create_token_pair(user.id)


@tokens.post("/refresh", response=TokenOut, deprecated=True)
def refresh_token(request, payload: RefreshIn):
    """Use `POST /api/v2/auth/refresh` instead."""
    claims = decode_token(payload.refresh, "refresh")
    if claims is None or not User.objects.filter(id=claims["sub"], is_active=True).exists():
        raise HttpError(401, "Invalid or expired refresh token")
    return create_token_pair(int(claims["sub"]))
```

`deprecated=True` tells clients to move on without breaking them. The endpoints keep working, and the docs show them as deprecated. The docstring says where to go instead. In the v1 schema:

```json
{
    "summary": "Obtain Token",
    "description": "Use `POST /api/v2/auth/token` instead.",
    "deprecated": true
}
```

**Go deeper:** [Operations: deprecated](../guide/operations.md#deprecated)

### Mounting both versions

Version 2 is a second `NinjaAPI` instance. Here is the complete `taskflow/api.py`:

```python title="taskflow/api.py" hl_lines="13 23-33"
from ninja import NinjaAPI

from accounts.auth import JWTAuth

DESCRIPTION = (
    "Track the tasks of your team's projects: members, labels, comments and attachments.\n\n"
    "Get a token from `POST /auth/token`, then click **Authorize** and paste it."
)

api = NinjaAPI(title="TaskFlow API", version="1.0", description=DESCRIPTION, auth=JWTAuth())

api.add_router("/auth", "accounts.api.router")
api.add_router("/auth", "accounts.api.tokens")
api.add_router("/projects", "projects.api.router")
api.add_router("/projects/{project_id}/tasks", "tasks.api.router")


@api.get("/health", auth=None, include_in_schema=False)
def health(request):
    return {"status": "ok"}


api_v2 = NinjaAPI(
    title="TaskFlow API",
    version="2.0",
    description=DESCRIPTION + "\n\nNew in 2.0: token responses use OAuth2 field names.",
    auth=JWTAuth(),
)

api_v2.add_router("/auth", "accounts.api.router")
api_v2.add_router("/auth", "accounts.api_v2.tokens")
api_v2.add_router("/projects", "projects.api.router")
api_v2.add_router("/projects/{project_id}/tasks", "tasks.api.router")
```

- Both APIs mount the same `signup`, projects and tasks routers. Each mount gets its own copy of the router's operations, bound to that API, so the two versions don't interfere. A bug fix in `tasks/api.py` reaches both versions at once.
- Only the `tokens` routers differ: `accounts.api.tokens` for version 1, and `accounts.api_v2.tokens` for version 2.
- `health` is registered on `api` only. `GET /api/v2/health` returns `404`.
- Mounting two routers at the same prefix, like the two `/auth` mounts, is fine as long as their paths don't overlap.

Mounting the same router twice on **one** API is different. Every operation's URL name must be unique within an API, so Django Ninja refuses the second mount:

```console
ninja.errors.ConfigError: Router is already mounted to this API. When mounting the same router multiple times, you must provide unique url_name_prefix for each mount.
```

Pass `url_name_prefix="..."` to the second `add_router()` call if you really need both mounts.

Then give version 2 its own URL prefix in `taskflow/urls.py`. Version 1 stays at `/api/`, so existing clients don't notice a thing:

```python title="taskflow/urls.py" hl_lines="6 10"
from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import path

from .api import api, api_v2

urlpatterns = [
    path("admin/", admin.site.urls),
    path("api/v2/", api_v2.urls),
    path("api/", api.urls),
] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
```

**Go deeper:** [Versioning](../guide/versioning.md#sharing-routers-between-versions), [Routers](../guide/routers.md#mounting-the-same-router-twice)

### Try it

Log in through version 2 with `POST /api/v2/auth/token` and `{"username": "alice", "password": "wonderland-42"}`:

```json
{
    "access_token": "eyJhbGciOiAiSFMyNTYiLCAidHlwIjogIkpXVCJ9.eyJzdWIiOiAiMSIsICJ0eXBlIjogImFjY2VzcyIsICJleHAiOiAxNzkwNTk1OTIyfQ.uKbqv565JqGDjMxFrjzfwEF2zf5mmDv4fiFK2W0lI64",
    "refresh_token": "eyJhbGciOiAiSFMyNTYiLCAidHlwIjogIkpXVCJ9.eyJzdWIiOiAiMSIsICJ0eXBlIjogInJlZnJlc2giLCAiZXhwIjogMTc5MTE5OTgyMn0.sPAI0PFLkazt-NUORo9u7INLum8b9HrTKnqRT1-XEY8",
    "token_type": "bearer",
    "expires_in": 900
}
```

The tokens are the same JWTs as before, and both APIs check them with the same `JWTAuth`. So a token from either version works on both: with this `access_token`, `GET /api/projects/` and `GET /api/v2/projects/` both return `200`.

The old field name no longer works on version 2. `POST /api/v2/auth/refresh` with `{"refresh": "..."}` returns `422`:

```json
{
    "detail": [
        {
            "type": "missing",
            "loc": [
                "body",
                "payload",
                "refresh_token"
            ],
            "msg": "Field required"
        }
    ]
}
```

With `{"refresh_token": "..."}` it returns a new token pair in the version 2 shape.

Now compare the two docs pages. <http://127.0.0.1:8000/api/docs> shows version **1.0**, with the two token endpoints marked as deprecated. <http://127.0.0.1:8000/api/v2/docs> shows version **2.0** and the extra line of description, and it loads its schema from `/api/v2/openapi.json`. Both schemas have the same 14 paths. Only `POST /auth/token` and `POST /auth/refresh` differ, and the component schemas `TokenOut` and `RefreshIn` of version 1 become `OAuthTokenOut` and `OAuthRefreshIn` in version 2.

**Go deeper:** [Versioning: multiple NinjaAPI instances](../guide/versioning.md#versioning-with-multiple-ninjaapi-instances)

### URL namespaces

Each `NinjaAPI` registers its URLs under its own namespace, `api-<version>` by default. The operation names come from the function names, so `reverse()` needs the namespace to tell the two versions apart:

```console
$ python manage.py shell
>>> from django.urls import reverse
>>> reverse('api-1.0:obtain_token')
'/api/auth/token'
>>> reverse('api-2.0:obtain_token')
'/api/v2/auth/token'
>>> reverse('api-2.0:openapi-view')
'/api/v2/docs'
```

Setting `version` on both APIs was enough to keep the namespaces apart. Two APIs with the same version (both default to `"1.0.0"`) share a namespace, and `manage.py check` warns about it:

```console
$ python manage.py check
System check identified some issues:

WARNINGS:
?: (urls.W005) URL namespace 'api-1.0.0' isn't unique. You may not be able to reverse all URLs in this namespace

System check identified 1 issue (0 silenced).
```

In that setup, `reverse('api-1.0.0:list_projects')` returned `'/api/v2/projects/'`, a URL from the wrong API. If two APIs must share a version, give them distinct `urls_namespace=` values.

**Go deeper:** [URLs & Reverse](../guide/urls.md#namespaces-urls_namespace)

## Testing both versions

A version is a promise to its clients, so it deserves its own tests. `TestClient` takes any `NinjaAPI`, so each version gets a client:

```python title="tests/test_versions.py" hl_lines="5-6 16-19"
from ninja.testing import TestClient

from taskflow.api import api, api_v2

client_v1 = TestClient(api)
client_v2 = TestClient(api_v2)


def test_v2_token_response(alice):
    response = client_v2.post("/auth/token", json={"username": "alice", "password": "wonderland-42"})
    assert response.status_code == 200
    data = response.json()
    assert data["token_type"] == "bearer"
    assert data["expires_in"] == 900

    # Both versions accept the same access token
    headers = {"Authorization": f"Bearer {data['access_token']}"}
    assert client_v1.get("/projects/", headers=headers).status_code == 200
    assert client_v2.get("/projects/", headers=headers).status_code == 200


def test_v2_refresh(alice):
    tokens = client_v2.post(
        "/auth/token", json={"username": "alice", "password": "wonderland-42"}
    ).json()
    response = client_v2.post("/auth/refresh", json={"refresh_token": tokens["refresh_token"]})
    assert response.status_code == 200
    assert set(response.json()) == {"access_token", "refresh_token", "token_type", "expires_in"}

    response = client_v2.post("/auth/refresh", json={"refresh_token": tokens["access_token"]})
    assert response.status_code == 401
```

Paths are relative to the API, so `/auth/token` on `client_v2` is `/api/v2/auth/token`. The Part 7 tests run against `api` and still pass, because version 1 behaves exactly as before:

```console
$ pytest
...
tests/test_auth.py ....                                                  [ 12%]
tests/test_projects.py ......                                            [ 30%]
tests/test_tasks.py ....................                                 [ 90%]
tests/test_versions.py ..                                                [ 96%]
tests/test_auth.py .                                                     [100%]

============================== 33 passed in 0.55s ==============================
```

pytest-django runs the tests that use the database first, which is why the last test of `test_auth.py`, `test_missing_token`, runs at the end.

**Go deeper:** [Testing](../guide/testing.md#basic-usage)

## Recap

- `NinjaAPI(title=..., version=..., description=...)` fills the `info` block of the schema. The description is Markdown.
- Summaries come from function names unless you pass `summary=`. Docstrings become descriptions, and `operationId` comes from the module and function name unless you pass `operation_id=`.
- `Field(description=..., examples=[...])` documents fields in body schemas and in filter schemas alike.
- `include_in_schema=False` hides an endpoint from the docs, and `deprecated=True` marks one as on its way out. Both keep working.
- A new version is a second `NinjaAPI` at its own URL prefix. Routers that didn't change are mounted on both, and whatever changed goes into a router of its own.
- Different versions get different URL namespaces, so `reverse()` and `manage.py check` stay happy.

## Next

That's the whole tutorial. TaskFlow has routers per app, nested schemas and computed fields, validation, JWT auth with roles, filtering and pagination, file uploads, a test suite and two documented API versions. From here, the [Guide](../guide/index.md) covers each feature in depth, including the ones this tutorial skipped, such as async views, throttling, custom renderers and parsers, and webhooks.
