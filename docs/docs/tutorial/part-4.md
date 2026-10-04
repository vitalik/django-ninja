# Part 4: Auth & permissions

Right now anyone who can reach the API can read and change every project. In this part you'll add JSON Web Tokens, written from scratch with the standard library, require them on every endpoint, and then decide what each user may do: project memberships with roles, queries scoped to the user's projects, and comments that only their author can edit.

!!! abstract "What you'll learn"
    - How to issue and verify JWT access and refresh tokens with nothing but the standard library
    - How to protect a whole API with an `HttpBearer` authenticator, and open up a few endpoints with `auth=None`
    - How to read the current user from `request.auth`
    - How to write one permission helper that returns `404` to non-members and `403` to members without the right role
    - How to scope every query to the user's projects, and add object-level rules for comments

    **Time:** about 15 minutes

## The accounts app

Users, tokens and the login endpoints get their own app:

```console
python manage.py startapp accounts
```

Delete `views.py` and `tests.py` again, and add the app to `INSTALLED_APPS`:

```python title="taskflow/settings.py" hl_lines="11"
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
    'accounts',
]
```

`UserOut` from Part 2 moves here too. The projects app needs it in this part, and `projects/schemas.py` can't import from `tasks/schemas.py`, which already imports `LabelOut` from `projects/schemas.py`. Cut it from `tasks/schemas.py`, along with its `User` import, and import it from the new module instead, so `TaskOut` keeps working:

```python title="tasks/schemas.py"
from accounts.schemas import UserOut
```

Then create `accounts/schemas.py`:

```python title="accounts/schemas.py"
from django.contrib.auth.models import User
from ninja import ModelSchema, Schema


class UserOut(ModelSchema):
    display_name: str

    class Meta:
        model = User
        fields = ["id", "username"]

    @staticmethod
    def resolve_display_name(user):
        return user.get_full_name() or user.username


class SignupIn(Schema):
    username: str
    password: str


class TokenIn(Schema):
    username: str
    password: str


class RefreshIn(Schema):
    refresh: str


class TokenOut(Schema):
    access: str
    refresh: str
```

## JSON Web Tokens from scratch

A JWT is three base64url strings joined by dots: a header, a payload of claims, and a signature over the first two. With HS256, the signature is an HMAC-SHA256 made with a secret key, here `settings.SECRET_KEY`. Anyone can read the claims, but no one can change them without the key.

That's short enough to write yourself:

```python title="accounts/tokens.py" hl_lines="21-23 33-44"
import base64
import hashlib
import hmac
import json
import time

from django.conf import settings

ACCESS_TOKEN_LIFETIME = 15 * 60  # 15 minutes
REFRESH_TOKEN_LIFETIME = 7 * 24 * 60 * 60  # 7 days


def b64encode(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode()


def b64decode(data: str) -> bytes:
    return base64.urlsafe_b64decode(data + "=" * (-len(data) % 4))


def sign(message: str) -> str:
    digest = hmac.new(settings.SECRET_KEY.encode(), message.encode(), hashlib.sha256).digest()
    return b64encode(digest)


def create_token(user_id: int, token_type: str, lifetime: int) -> str:
    header = b64encode(json.dumps({"alg": "HS256", "typ": "JWT"}).encode())
    claims = {"sub": str(user_id), "type": token_type, "exp": int(time.time()) + lifetime}
    payload = b64encode(json.dumps(claims).encode())
    return f"{header}.{payload}.{sign(f'{header}.{payload}')}"


def decode_token(token: str, token_type: str) -> dict | None:
    """Return the claims of a valid, unexpired token of the given type, else None."""
    try:
        header, payload, signature = token.split(".")
    except ValueError:
        return None
    if not hmac.compare_digest(signature.encode(), sign(f"{header}.{payload}").encode()):
        return None
    claims = json.loads(b64decode(payload))
    if claims["type"] != token_type or claims["exp"] < time.time():
        return None
    return claims


def create_token_pair(user_id: int) -> dict:
    return {
        "access": create_token(user_id, "access", ACCESS_TOKEN_LIFETIME),
        "refresh": create_token(user_id, "refresh", REFRESH_TOKEN_LIFETIME),
    }
```

- JWTs use base64url without the `=` padding. `b64decode` adds the padding back before decoding.
- `sub` (the user id) and `exp` (expiry, in Unix seconds) are standard claims. `type` is a claim of your own that tells access and refresh tokens apart, so a refresh token can't be used to call the API.
- `decode_token` checks the signature before it reads the payload, so every claim it looks at was signed by you. `hmac.compare_digest` compares in constant time, which doesn't leak how many characters matched.
- The header is signed, but never trusted: the code always verifies with HS256, whatever `alg` the token claims. That rules out the classic `"alg": "none"` attack.
- Anything wrong, whether a malformed token, a bad signature, the wrong type or an expired token, returns `None`. The caller doesn't need to know which.

The access token lives 15 minutes. The refresh token lives 7 days and can only be exchanged for a new pair.

## Protecting the API

`HttpBearer` reads the `Authorization: Bearer <token>` header and passes the token to your `authenticate()` method. Whatever it returns becomes `request.auth`. `None` means the request is rejected with `401`:

```python title="accounts/auth.py"
from django.contrib.auth.models import User
from ninja.security import HttpBearer

from .tokens import decode_token


class JWTAuth(HttpBearer):
    def authenticate(self, request, token):
        claims = decode_token(token, "access")
        if claims is None:
            return None
        return User.objects.filter(id=claims["sub"], is_active=True).first()
```

It returns the `User`, so every view can use `request.auth` as the current user. A deactivated user's tokens stop working at once, even before they expire.

Set it on the `NinjaAPI`, so every operation requires a token, and mount the new router:

```python title="taskflow/api.py" hl_lines="3 5 7"
from ninja import NinjaAPI

from accounts.auth import JWTAuth

api = NinjaAPI(title="TaskFlow API", auth=JWTAuth())

api.add_router("/auth", "accounts.api.router")
api.add_router("/projects", "projects.api.router")
api.add_router("/projects/{project_id}/tasks", "tasks.api.router")
```

The auth endpoints themselves must work without a token. `auth=None` on their router opts them out:

```python title="accounts/api.py" hl_lines="11"
from django.contrib.auth import authenticate
from django.contrib.auth.models import User
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError
from ninja import Router, Status
from ninja.errors import HttpError

from .schemas import RefreshIn, SignupIn, TokenIn, TokenOut, UserOut
from .tokens import create_token_pair, decode_token

router = Router(tags=["auth"], auth=None)


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


@router.post("/token", response=TokenOut)
def obtain_token(request, payload: TokenIn):
    user = authenticate(username=payload.username, password=payload.password)
    if user is None:
        raise HttpError(401, "Invalid username or password")
    return create_token_pair(user.id)


@router.post("/refresh", response=TokenOut)
def refresh_token(request, payload: RefreshIn):
    claims = decode_token(payload.refresh, "refresh")
    if claims is None or not User.objects.filter(id=claims["sub"], is_active=True).exists():
        raise HttpError(401, "Invalid or expired refresh token")
    return create_token_pair(int(claims["sub"]))
```

- `auth` resolves from the most specific level: operation, then router, then API. `auth=None` is how you turn it off for part of an API that sets it globally.
- `signup` runs Django's `AUTH_PASSWORD_VALIDATORS` and returns their messages as a `400`.
- `obtain_token` uses Django's `authenticate()`, so it respects inactive users and any authentication backends you configure.

### Try it

Alice and Bob from Part 2 have no passwords yet. Set them in the shell:

```console
$ python manage.py shell
>>> alice = User.objects.get(username="alice")
>>> alice.set_password("wonderland-42")
>>> alice.save()
>>> bob = User.objects.get(username="bob")
>>> bob.set_password("builder-42")
>>> bob.save()
```

Without a token, every endpoint except the three under `/api/auth/` now returns `401`:

```console
$ curl http://127.0.0.1:8000/api/projects/
{"detail": "Unauthorized"}
```

Log in:

```console
$ curl -X POST http://127.0.0.1:8000/api/auth/token -H "Content-Type: application/json" -d '{"username": "alice", "password": "wonderland-42"}'
{"access": "eyJhbGciOiAiSFMyNTYiLCAidHlwIjogIkpXVCJ9.eyJzdWIiOiAiMSIsICJ0eXBlIjogImFjY2VzcyIsICJleHAiOiAxNzkwNTk0MTkwfQ.GaiXckAgDYsFg8sT9aw69lVVvTQicl6jgm8B6EOvkec", "refresh": "eyJhbGciOiAiSFMyNTYiLCAidHlwIjogIkpXVCJ9.eyJzdWIiOiAiMSIsICJ0eXBlIjogInJlZnJlc2giLCAiZXhwIjogMTc5MTE5ODA5MH0.2T6GPT9KOTlhyGKNlGgs74W1LmviG5UneZA_K4gwgvc"}
```

A wrong password gives `401` with `{"detail": "Invalid username or password"}`. The middle part of the access token is the payload, readable by anyone:

```console
>>> from accounts.tokens import b64decode
>>> b64decode("eyJzdWIiOiAiMSIsICJ0eXBlIjogImFjY2VzcyIsICJleHAiOiAxNzkwNTk0MTkwfQ")
b'{"sub": "1", "type": "access", "exp": 1790594190}'
```

Send the access token in the `Authorization` header. With `TOKEN` set to the `access` value, `GET /api/projects/` returns the projects again:

```console
$ curl http://127.0.0.1:8000/api/projects/ -H "Authorization: Bearer $TOKEN"
```

When it expires, post the refresh token as `{"refresh": "..."}` to `/api/auth/refresh` for a new pair. An access token is refused there, because its `type` claim is wrong:

```json
{
    "detail": "Invalid or expired refresh token"
}
```

In the interactive docs at `/api/docs`, the operations now show a lock, and an **Authorize** button appears at the top. Paste an access token there (without the `Bearer ` prefix) and Swagger UI sends it with every request you try. The three auth endpoints have no lock, because they have no auth.

**Go deeper:** [Authentication](../guide/authentication.md#http-bearer), [Authentication: auth at different levels](../guide/authentication.md#applying-auth-at-different-levels)

## Memberships and roles

Authentication tells you who is calling. Authorization decides what they may do. In TaskFlow that depends on the project: a user can be the owner of one project and a plain member of another. That's a `Membership` with a role. Add it between `Project` and `Label`, along with the `settings` import:

```python title="projects/models.py"
from django.conf import settings
from django.db import models

...

class Role(models.TextChoices):
    OWNER = "owner"
    ADMIN = "admin"
    MEMBER = "member"


class Membership(models.Model):
    project = models.ForeignKey(Project, related_name="memberships", on_delete=models.CASCADE)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, related_name="memberships", on_delete=models.CASCADE
    )
    role = models.CharField(max_length=10, choices=Role, default=Role.MEMBER)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["project", "user"], name="unique_membership"),
        ]

    def __str__(self):
        return f"{self.user} in {self.project} ({self.role})"
```

```console
$ python manage.py makemigrations
Migrations for 'projects':
  projects/migrations/0003_membership.py
    + Create model Membership
$ python manage.py migrate
```

The roles in TaskFlow:

| Role | Can |
| --- | --- |
| `member` | see the project, work on its tasks, comment |
| `admin` | also edit the project and create labels |
| `owner` | also delete the project, add members, and delete anyone's comments |

Your existing projects have no members yet, so once the next step is in place nobody would see them. Make Alice their owner:

```console
$ python manage.py shell
>>> alice = User.objects.get(username="alice")
>>> for project in Project.objects.all():
...     Membership.objects.create(project=project, user=alice, role="owner")
...
<Membership: alice in Website redesign (owner)>
<Membership: alice in Mobile app (owner)>
```

### One helper for every check

Almost every endpoint needs the same check: is this user a member of this project, and does their role allow the action? Put it in one function:

```python title="projects/permissions.py"
from django.shortcuts import get_object_or_404
from ninja.errors import HttpError

from .models import Membership


def get_project_or_404(user, project_id, roles=None):
    """Return the project if `user` is a member, with one of `roles` if given.

    Non-members get a 404, so they can't tell the project exists.
    Members without the right role get a 403.
    """
    membership = get_object_or_404(
        Membership.objects.select_related("project"), project_id=project_id, user=user
    )
    if roles and membership.role not in roles:
        raise HttpError(403, f"This needs the {' or '.join(roles)} role")
    return membership.project
```

- One query finds the membership and the project together.
- A non-member gets exactly the same `404` as for a project id that doesn't exist. A `403` would confirm that project 1 exists.
- A member who lacks the role gets a `403` that says which role is needed. They can already see the project, so there's nothing to hide.

It's a plain function, not a decorator: the view calls it and gets the project back, which it needs anyway.

## Scoping projects

Now rewrite the projects endpoints so every query starts from the user's memberships. Two schemas for managing members go at the end of `projects/schemas.py`, which now imports `UserOut` and `Role`:

```python title="projects/schemas.py"
from ninja import ModelSchema, Schema

from accounts.schemas import UserOut

from .models import Label, Project, Role

...

class MemberIn(Schema):
    username: str
    role: Role = Role.MEMBER


class MemberOut(Schema):
    user: UserOut
    role: Role
```

```python title="projects/api.py" hl_lines="16 33 44 53 59 63-77"
from django.contrib.auth.models import User
from django.db.models import Count, Q
from django.shortcuts import get_object_or_404
from ninja import Router, Status
from ninja.errors import HttpError

from .models import Project, Role
from .permissions import get_project_or_404
from .schemas import LabelIn, LabelOut, MemberIn, MemberOut, ProjectIn, ProjectOut

router = Router(tags=["projects"])


def projects_with_counts(user):
    return (
        Project.objects.filter(memberships__user=user)
        .annotate(
            task_count=Count("tasks"),
            unassigned_task_count=Count("tasks", filter=Q(tasks__assignee=None)),
        )
        .prefetch_related("labels")
    )


@router.get("/", response=list[ProjectOut])
def list_projects(request):
    return projects_with_counts(request.auth).order_by("id")


@router.post("/", response={201: ProjectOut})
def create_project(request, payload: ProjectIn):
    project = Project.objects.create(**payload.dict())
    project.memberships.create(user=request.auth, role=Role.OWNER)
    return Status(201, projects_with_counts(request.auth).get(id=project.id))


@router.get("/{project_id}", response=ProjectOut)
def get_project(request, project_id: int):
    return get_object_or_404(projects_with_counts(request.auth), id=project_id)


@router.put("/{project_id}", response=ProjectOut)
def update_project(request, project_id: int, payload: ProjectIn):
    project = get_project_or_404(request.auth, project_id, roles=[Role.OWNER, Role.ADMIN])
    for attr, value in payload.dict().items():
        setattr(project, attr, value)
    project.save()
    return projects_with_counts(request.auth).get(id=project.id)


@router.delete("/{project_id}", response={204: None})
def delete_project(request, project_id: int):
    get_project_or_404(request.auth, project_id, roles=[Role.OWNER]).delete()
    return Status(204, None)


@router.post("/{project_id}/labels", response={201: LabelOut})
def create_label(request, project_id: int, payload: LabelIn):
    project = get_project_or_404(request.auth, project_id, roles=[Role.OWNER, Role.ADMIN])
    return Status(201, project.labels.create(**payload.dict()))


@router.get("/{project_id}/members", response=list[MemberOut])
def list_members(request, project_id: int):
    project = get_project_or_404(request.auth, project_id)
    return project.memberships.select_related("user").order_by("id")


@router.post("/{project_id}/members", response={201: MemberOut})
def add_member(request, project_id: int, payload: MemberIn):
    project = get_project_or_404(request.auth, project_id, roles=[Role.OWNER])
    user = User.objects.filter(username=payload.username).first()
    if user is None:
        raise HttpError(400, f"User {payload.username} does not exist")
    if project.memberships.filter(user=user).exists():
        raise HttpError(409, f"{user.username} is already a member")
    return Status(201, project.memberships.create(user=user, role=payload.role))
```

- `projects_with_counts()` takes the user and filters on their memberships, so list and get only ever see the user's projects. The filter comes before `annotate()`, and a user has at most one membership per project, so the task counts stay correct.
- The user who creates a project becomes its owner.
- Update, delete and labels call `get_project_or_404()` with the roles they need.
- `MemberOut` is a plain `Schema`, and `list_members` returns `Membership` objects. Django Ninja reads `user` and `role` from each one as attributes.

### Try it

Sign up a third user with `POST /api/auth/signup`. A weak password, as in `{"username": "carol", "password": "carol"}`, is rejected with the validators' messages:

```json
{
    "detail": "This password is too short. It must contain at least 8 characters. This password is too common."
}
```

`{"username": "carol", "password": "sunflower-77"}` returns `201`:

```json
{
    "display_name": "carol",
    "id": 3,
    "username": "carol"
}
```

Log in as Carol. `GET /api/projects/` returns `[]`, and `GET /api/projects/1` returns `404`:

```json
{
    "detail": "Not Found: No Project matches the given query."
}
```

The part after `Not Found` comes from Django's `Http404` message, and Django Ninja only adds it while `DEBUG` is on. With `DEBUG = False`, every `404` here is just `{"detail": "Not Found"}`, so it doesn't matter which query didn't find anything. Carol can create her own project, and she's its owner.

As Alice, add Bob to project 1 with `POST /api/projects/1/members` and `{"username": "bob"}`:

```json
{
    "user": {
        "display_name": "bob",
        "id": 2,
        "username": "bob"
    },
    "role": "member"
}
```

Bob can now see the project and its tasks. He can't rename it with `PUT /api/projects/1`:

```json
{
    "detail": "This needs the owner or admin role"
}
```

and `DELETE /api/projects/1` gives `{"detail": "This needs the owner role"}`.

**Go deeper:** [Authentication](../guide/authentication.md#authorization-and-permissions), [Errors & Exception Handling](../guide/errors.md#throwing-http-errors)

## Tasks and comments

Tasks belong to a project, so they're covered by the same check. The new piece is comments, where the rule depends on the comment itself. Add the model to `tasks/models.py`:

```python title="tasks/models.py"
class Comment(models.Model):
    task = models.ForeignKey(Task, related_name="comments", on_delete=models.CASCADE)
    author = models.ForeignKey(
        settings.AUTH_USER_MODEL, related_name="comments", on_delete=models.CASCADE
    )
    body = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Comment by {self.author} on {self.task}"
```

```console
$ python manage.py makemigrations
Migrations for 'tasks':
  tasks/migrations/0004_comment.py
    + Create model Comment
$ python manage.py migrate
```

Add the comment schemas to `tasks/schemas.py`, and `Comment` to its model import:

```python title="tasks/schemas.py"
from ninja import ModelSchema, Schema
from pydantic import field_validator, model_validator
from pydantic_core import PydanticCustomError

from accounts.schemas import UserOut
from projects.schemas import LabelOut

from .models import Comment, Priority, Task, TaskStatus

...

class CommentIn(ModelSchema):
    class Meta:
        model = Comment
        fields = ["body"]


class CommentOut(ModelSchema):
    author: UserOut

    class Meta:
        model = Comment
        fields = ["id", "body", "created_at"]
```

Here's the full `tasks/api.py`:

```python title="tasks/api.py" hl_lines="14-16 21-22 31 37 70-103"
from django.shortcuts import get_object_or_404
from ninja import PatchDict, Path, Router, Status
from ninja.errors import HttpError

from projects.models import Role
from projects.permissions import get_project_or_404

from .models import ALLOWED_TRANSITIONS, Priority, Task
from .schemas import CommentIn, CommentOut, StatusIn, TaskIn, TaskOut, TaskUpdate

router = Router(tags=["tasks"])


def get_task_or_404(user, project_id, task_id):
    project = get_project_or_404(user, project_id)
    return get_object_or_404(project.tasks, id=task_id)


def check_relations(project, payload):
    assignee_id = payload.assignee_id
    if assignee_id is not None and not project.memberships.filter(user_id=assignee_id).exists():
        raise HttpError(400, f"User {assignee_id} is not a member of this project")
    labels = list(project.labels.filter(id__in=payload.label_ids))
    if len(labels) != len(set(payload.label_ids)):
        raise HttpError(400, "Unknown label id for this project")
    return labels


@router.get("/", response=list[TaskOut])
def list_tasks(request, project_id: Path[int]):
    project = get_project_or_404(request.auth, project_id)
    return project.tasks.select_related("assignee").prefetch_related("labels").order_by("id")


@router.post("/", response={201: TaskOut})
def create_task(request, project_id: Path[int], payload: TaskIn):
    project = get_project_or_404(request.auth, project_id)
    labels = check_relations(project, payload)
    task = Task.objects.create(project=project, **payload.dict(exclude={"label_ids"}))
    task.labels.set(labels)
    return Status(201, task)


@router.get("/{task_id}", response=TaskOut)
def get_task(request, project_id: Path[int], task_id: int):
    return get_task_or_404(request.auth, project_id, task_id)


@router.patch("/{task_id}", response=TaskOut)
def update_task(request, project_id: Path[int], task_id: int, payload: PatchDict[TaskUpdate]):
    task = get_task_or_404(request.auth, project_id, task_id)
    for attr, value in payload.items():
        setattr(task, attr, value)
    if task.priority == Priority.URGENT and task.due_date is None:
        raise HttpError(400, "Urgent tasks need a due date")
    task.save()
    return task


@router.post("/{task_id}/status", response=TaskOut)
def change_status(request, project_id: Path[int], task_id: int, payload: StatusIn):
    task = get_task_or_404(request.auth, project_id, task_id)
    if payload.status not in ALLOWED_TRANSITIONS[task.status]:
        raise HttpError(409, f"Can't move a task from {task.status} to {payload.status}")
    task.status = payload.status
    task.save()
    return task


@router.get("/{task_id}/comments", response=list[CommentOut])
def list_comments(request, project_id: Path[int], task_id: int):
    task = get_task_or_404(request.auth, project_id, task_id)
    return task.comments.select_related("author").order_by("id")


@router.post("/{task_id}/comments", response={201: CommentOut})
def add_comment(request, project_id: Path[int], task_id: int, payload: CommentIn):
    task = get_task_or_404(request.auth, project_id, task_id)
    return Status(201, task.comments.create(author=request.auth, body=payload.body))


@router.put("/{task_id}/comments/{comment_id}", response=CommentOut)
def update_comment(
    request, project_id: Path[int], task_id: int, comment_id: int, payload: CommentIn
):
    task = get_task_or_404(request.auth, project_id, task_id)
    comment = get_object_or_404(task.comments, id=comment_id)
    if comment.author != request.auth:
        raise HttpError(403, "Only the author can edit a comment")
    comment.body = payload.body
    comment.save()
    return comment


@router.delete("/{task_id}/comments/{comment_id}", response={204: None})
def delete_comment(request, project_id: Path[int], task_id: int, comment_id: int):
    task = get_task_or_404(request.auth, project_id, task_id)
    comment = get_object_or_404(task.comments, id=comment_id)
    if comment.author != request.auth:
        # Anyone else needs to own the project
        get_project_or_404(request.auth, project_id, roles=[Role.OWNER])
    comment.delete()
    return Status(204, None)
```

- `get_task_or_404()` goes through the project check first, then looks the task up in `project.tasks`. Every task and comment endpoint uses it, so none of them can reach another project's data.
- `check_relations()` now only accepts assignees who are members of the project. Part 2's check for any existing user would let you assign tasks to strangers.
- Comments are looked up through `task.comments`, so a comment id from another task is a `404`.
- The comment author comes from `request.auth`, never from the request body.
- These are **object-level** rules: they depend on the comment, not only on the project role. Only the author may edit a comment. The author or the project owner may delete it, and for anyone else the view reuses `get_project_or_404()` with `roles=[Role.OWNER]`.

### Try it

As Bob, post a comment on task 2 with `POST /api/projects/1/tasks/2/comments` and `{"body": "The footer links point to the old domain."}`:

```json
{
    "author": {
        "display_name": "bob",
        "id": 2,
        "username": "bob"
    },
    "id": 1,
    "body": "The footer links point to the old domain.",
    "created_at": "2026-09-28T11:00:54.225Z"
}
```

Alice replies with a comment of her own, `{"body": "Good catch, thanks!"}` (id 2). She owns the project, but that doesn't let her edit Bob's words. `PUT /api/projects/1/tasks/2/comments/1` as Alice returns:

```json
{
    "detail": "Only the author can edit a comment"
}
```

The same request as Bob returns `200` with the new body. Bob can't delete Alice's comment 2:

```json
{
    "detail": "This needs the owner role"
}
```

But Alice, as the owner, can delete Bob's comment 1: `DELETE /api/projects/1/tasks/2/comments/1` returns `204`. And Carol, who isn't a member, gets a `404` for the task's comments, like for everything else in the project.

**Go deeper:** [Authentication](../guide/authentication.md#authorization-and-permissions), [Decorators](../guide/decorators.md#reusable-permission-checks)

## Recap

- A JWT is a signed, readable payload. HS256 with `hmac`, `hashlib`, `base64` and `json` fits in a module of about 50 lines. Verify the signature before reading the claims, and check the expiry and the token type.
- `HttpBearer` reads the `Authorization: Bearer` header. What `authenticate()` returns becomes `request.auth`, and `None` means `401`.
- `NinjaAPI(auth=...)` protects every endpoint. `auth=None` on a router or an operation opts it out, as for login and refresh.
- One helper, `get_project_or_404(user, project_id, roles=...)`, answers `404` to non-members and `403` to members without the right role.
- Start every query from the user's memberships, and take ownership fields such as a comment's author from `request.auth`.
- Rules about a single object, such as who may edit a comment, go in the view, after the object is loaded.

## Next

The task list returns everything at once. In [Part 5: Filtering, search, ordering & pagination](part-5.md), you'll filter tasks by status, assignee and label, search them, sort them, and paginate tasks and comments.
