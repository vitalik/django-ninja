# Part 7: Testing

So far you've checked every feature by hand, with curl and the shell. In this part you'll turn those checks into a pytest suite that runs in about half a second. Django Ninja's `TestClient` calls your operations directly, so tests send JSON, form data, files and tokens without a running server.

!!! abstract "What you'll learn"
    - How to set up pytest and pytest-django for a Django Ninja project
    - How to write fixtures for users, projects with memberships, and logged-in clients
    - How `TestClient` calls an API, and how to send tokens, query strings and files with it
    - How to test validation errors, permissions and filters, and cover many cases with `parametrize`
    - How to keep uploads and password hashing from slowing down or littering your tests

    **Time:** about 15 minutes

## Setting up pytest

The tests need two packages. They're only used in development, so they don't join Django and Django Ninja as runtime dependencies:

```console
$ pip install pytest pytest-django
```

pytest-django creates a test database for every run, applies your migrations to it, and wraps each test in a transaction that is rolled back afterwards. It needs to know your settings module. Create `pytest.ini` next to `manage.py`:

```ini title="pytest.ini"
[pytest]
DJANGO_SETTINGS_MODULE = taskflow.settings
testpaths = tests
```

Part 1 deleted the `tests.py` files from the apps. The tests go into a top-level `tests/` folder instead, because most of them cross app boundaries: a task test needs users from `accounts` and a project from `projects`. `testpaths` tells pytest to look there. The folder needs no `__init__.py`. pytest-django puts the folder with `manage.py` on the import path, so `from taskflow.api import api` works in tests.

With SQLite, the test database lives in memory. Your `db.sqlite3` and the data from earlier parts are never touched.

**Go deeper:** [Testing](../guide/testing.md#basic-usage)

## Fixtures

Almost every test needs the same things: a few users, a project with an owner and a member, and a client that sends a token. pytest fixtures build them on demand. Fixtures in `tests/conftest.py` are available to every test file without an import:

```python title="tests/conftest.py" hl_lines="10-13 40-48"
import pytest
from django.contrib.auth.models import User
from ninja.testing import TestClient

from accounts.tokens import create_token_pair
from projects.models import Project, Role
from taskflow.api import api


@pytest.fixture(autouse=True)
def test_settings(settings, tmp_path):
    settings.MEDIA_ROOT = tmp_path  # uploads go to a temporary folder
    settings.PASSWORD_HASHERS = ["django.contrib.auth.hashers.MD5PasswordHasher"]


@pytest.fixture
def alice(db):
    return User.objects.create_user("alice", password="wonderland-42")


@pytest.fixture
def bob(db):
    return User.objects.create_user("bob", password="builder-42")


@pytest.fixture
def carol(db):
    return User.objects.create_user("carol", password="sunflower-77")


@pytest.fixture
def project(alice, bob):
    """Alice owns the project, bob is a member."""
    project = Project.objects.create(name="Website redesign", description="New marketing site")
    project.memberships.create(user=alice, role=Role.OWNER)
    project.memberships.create(user=bob, role=Role.MEMBER)
    return project


@pytest.fixture
def client_for():
    """Return a TestClient that is logged in as the given user."""

    def make_client(user):
        token = create_token_pair(user.id)["access"]
        return TestClient(api, headers={"Authorization": f"Bearer {token}"})

    return make_client
```

- `test_settings` runs for every test because of `autouse=True`. It uses pytest-django's `settings` fixture, which restores the original values after each test.
- `MEDIA_ROOT` points to `tmp_path`, a fresh temporary folder per test, so upload tests don't write into your `media/` folder.
- Django's default password hasher is slow on purpose. Every `create_user()` and every login pays for it. The MD5 hasher is unsafe for real passwords, but fine for test users. On the machine used for this tutorial, the suite takes 51 seconds without that line and half a second with it.
- The user fixtures take pytest-django's `db` fixture, which allows database access. `project` depends on `alice` and `bob`, so asking for `project` creates all three.
- `client_for` is a factory fixture. A test can call it for any user, even several times, as in `client_for(alice)` and `client_for(bob)`. It creates the token with `create_token_pair()` from Part 4 instead of calling `/auth/token`, which keeps the tests of other endpoints independent of the login endpoint.
- `TestClient(api, headers=...)` sends those headers with every request. You used the same client in the shell in Part 5.

`TestClient` doesn't go through `urls.py` or Django's middleware. It finds the operation in the `NinjaAPI` and calls it with a fake request. Paths are therefore relative to the API: `/projects/`, not `/api/projects/`. Everything that is part of the operation still runs: authentication, validation, your view, the response schema and the error handlers. A path that matches no operation raises an exception instead of returning `404`, so a typo in a test fails loudly.

**Go deeper:** [Testing](../guide/testing.md#headers-and-cookies)

## Testing authentication

The auth tests use a plain client without a token, because getting one is what they test. Create `tests/test_auth.py`:

```python title="tests/test_auth.py" hl_lines="6 30"
from ninja.testing import TestClient

from accounts.tokens import create_token
from taskflow.api import api

client = TestClient(api)


def test_obtain_token(alice):
    response = client.post("/auth/token", json={"username": "alice", "password": "wonderland-42"})
    assert response.status_code == 200
    token = response.json()["access"]

    response = client.get("/projects/", headers={"Authorization": f"Bearer {token}"})
    assert response.status_code == 200


def test_wrong_password(alice):
    response = client.post("/auth/token", json={"username": "alice", "password": "nope"})
    assert response.status_code == 401
    assert response.json() == {"detail": "Invalid username or password"}


def test_missing_token():
    response = client.get("/projects/")
    assert response.status_code == 401


def test_expired_token(alice):
    token = create_token(alice.id, "access", lifetime=-1)
    response = client.get("/projects/", headers={"Authorization": f"Bearer {token}"})
    assert response.status_code == 401


def test_refresh_token_is_not_an_access_token(alice):
    response = client.post("/auth/token", json={"username": "alice", "password": "wonderland-42"})
    refresh = response.json()["refresh"]
    response = client.get("/projects/", headers={"Authorization": f"Bearer {refresh}"})
    assert response.status_code == 401
```

- `json=` serializes the body, like a client sending `Content-Type: application/json`. `response.json()` decodes the answer.
- `headers=` on a single request adds to the client's default headers, or overrides them.
- Waiting 15 minutes for a token to expire isn't an option. `create_token()` takes the lifetime as an argument, so a negative one creates a token that expired a second ago.
- `test_missing_token` needs no database. `HttpBearer` rejects a request without an `Authorization` header before `authenticate()` runs.

**Go deeper:** [Testing](../guide/testing.md#testing-authenticated-views)

## Projects and permissions

Most of the value of an API test suite is in the permission rules, because a missing check doesn't show up when you try the happy path. Create `tests/test_projects.py`:

```python title="tests/test_projects.py" hl_lines="24-32"
from projects.models import Role


def test_create_project(alice, client_for):
    response = client_for(alice).post(
        "/projects/", json={"name": "Launch", "description": "Product launch"}
    )
    assert response.status_code == 201
    data = response.json()
    assert data["name"] == "Launch"
    assert data["task_count"] == 0
    assert alice.memberships.get(project_id=data["id"]).role == Role.OWNER


def test_list_only_my_projects(alice, carol, project, client_for):
    client_for(carol).post(
        "/projects/", json={"name": "Carol's garden", "description": "Vegetables"}
    )

    response = client_for(alice).get("/projects/")
    assert [p["name"] for p in response.json()] == ["Website redesign"]


def test_non_member_gets_404(carol, project, client_for):
    response = client_for(carol).get(f"/projects/{project.id}")
    assert response.status_code == 404


def test_member_cannot_delete(bob, project, client_for):
    response = client_for(bob).delete(f"/projects/{project.id}")
    assert response.status_code == 403
    assert response.json() == {"detail": "This needs the owner role"}


def test_owner_can_update(alice, project, client_for):
    response = client_for(alice).put(
        f"/projects/{project.id}", json={"name": "Website v2", "description": "Round two"}
    )
    assert response.status_code == 200
    project.refresh_from_db()
    assert project.name == "Website v2"


def test_add_member_twice(alice, bob, project, client_for):
    response = client_for(alice).post(f"/projects/{project.id}/members", json={"username": "bob"})
    assert response.status_code == 409
    assert response.json() == {"detail": "bob is already a member"}
```

- The highlighted tests pin down the two sides of `get_project_or_404` from Part 4: a non-member gets `404`, a member without the right role gets `403`.
- Tests can check the database as well as the response. `test_create_project` confirms that the creator became the owner, and `test_owner_can_update` reloads the project with `refresh_from_db()`.
- Each test starts with an empty database. Carol's project in `test_list_only_my_projects` is gone before the next test runs.

## Tasks: validation, workflows and filters

The task tests share one more fixture, a task in the project. Create `tests/test_tasks.py`:

```python title="tests/test_tasks.py" hl_lines="9-11 31-33"
from datetime import date

import pytest
from django.core.files.uploadedfile import SimpleUploadedFile

from tasks.models import Priority, Task, TaskStatus


@pytest.fixture
def task(project, alice):
    return project.tasks.create(title="Draft the sitemap", assignee=alice)


def test_create_task(alice, bob, project, client_for):
    label = project.labels.create(name="design")
    response = client_for(alice).post(
        f"/projects/{project.id}/tasks/",
        json={"title": "  Pick fonts ", "assignee_id": bob.id, "label_ids": [label.id]},
    )
    assert response.status_code == 201
    data = response.json()
    assert data["title"] == "Pick fonts"
    assert data["assignee"]["username"] == "bob"
    assert data["labels"] == [{"id": label.id, "name": "design", "color": "#808080"}]
    assert data["status"] == "todo"


def test_blank_title(alice, project, client_for):
    response = client_for(alice).post(f"/projects/{project.id}/tasks/", json={"title": "   "})
    assert response.status_code == 422
    assert response.json()["detail"] == [
        {"type": "blank", "loc": ["body", "payload", "title"], "msg": "Title can't be blank"}
    ]


def test_urgent_task_needs_due_date(alice, project, client_for):
    response = client_for(alice).post(
        f"/projects/{project.id}/tasks/", json={"title": "Fix login", "priority": Priority.URGENT}
    )
    assert response.status_code == 422
    assert response.json()["detail"][0]["msg"] == "Value error, Urgent tasks need a due date"


def test_assignee_must_be_member(alice, carol, project, client_for):
    response = client_for(alice).post(
        f"/projects/{project.id}/tasks/", json={"title": "Pick fonts", "assignee_id": carol.id}
    )
    assert response.status_code == 400


def test_non_member_cannot_see_tasks(carol, task, client_for):
    response = client_for(carol).get(f"/projects/{task.project_id}/tasks/{task.id}")
    assert response.status_code == 404


def test_patch_changes_only_sent_fields(alice, task, client_for):
    response = client_for(alice).patch(
        f"/projects/{task.project_id}/tasks/{task.id}", json={"due_date": "2026-10-15"}
    )
    assert response.status_code == 200
    task.refresh_from_db()
    assert task.due_date == date(2026, 10, 15)
    assert task.title == "Draft the sitemap"
```

- Fixtures can live in a test file too. `task` is only used here, so it doesn't need to be in `conftest.py`.
- `test_blank_title` compares the whole `detail` list. It holds the same `blank` error you saw in Part 3. A change to the error's type, location or message breaks the test, which is what you want once clients depend on it.
- `test_create_task` also checks that the title was stripped and that the nested `assignee` and `labels` from Part 2 are in the response.
- `Priority.URGENT` can go straight into `json=`. `IntegerChoices` members are integers, so it's sent as `4`.

### Many cases, one test

The status workflow from Part 3 has a table of allowed moves. `@pytest.mark.parametrize` turns a table of cases into one test each. Add it to `tests/test_tasks.py`:

```python title="tests/test_tasks.py" hl_lines="1-9"
@pytest.mark.parametrize(
    "old, new, status_code",
    [
        (TaskStatus.TODO, TaskStatus.IN_PROGRESS, 200),
        (TaskStatus.IN_PROGRESS, TaskStatus.DONE, 200),
        (TaskStatus.TODO, TaskStatus.DONE, 409),
        (TaskStatus.DONE, TaskStatus.TODO, 409),
    ],
)
def test_status_transitions(alice, task, client_for, old, new, status_code):
    Task.objects.filter(id=task.id).update(status=old)
    response = client_for(alice).post(
        f"/projects/{task.project_id}/tasks/{task.id}/status", json={"status": new}
    )
    assert response.status_code == status_code
```

The test sets the starting status directly in the database. Going through the API would make a test for `done` depend on two earlier moves working.

Filters work the same way: one fixture with a few tasks, and a table of query strings with the titles each should return. Add both:

```python title="tests/test_tasks.py" hl_lines="22-32"
@pytest.fixture
def sample_tasks(project, bob):
    bug = project.labels.create(name="bug")
    project.tasks.create(
        title="Fix mobile menu", assignee=bob, priority=Priority.URGENT, due_date=date(2026, 10, 1)
    ).labels.add(bug)
    project.tasks.create(
        title="Set up analytics",
        description="Page views",
        status=TaskStatus.IN_PROGRESS,
        due_date=date(2026, 10, 20),
    )
    project.tasks.create(
        title="Compress images",
        assignee=bob,
        priority=Priority.HIGH,
        due_date=date(2026, 10, 3),
        status=TaskStatus.DONE,
    )


@pytest.mark.parametrize(
    "query, titles",
    [
        ("", ["Fix mobile menu", "Set up analytics", "Compress images"]),
        ("status=todo&status=in_progress", ["Fix mobile menu", "Set up analytics"]),
        ("assignee=bob&label=bug", ["Fix mobile menu"]),
        ("due_before=2026-10-05", ["Fix mobile menu", "Compress images"]),
        ("search=VIEWS", ["Set up analytics"]),
        ("ordering=-priority", ["Fix mobile menu", "Compress images", "Set up analytics"]),
    ],
)
def test_filter_tasks(alice, project, sample_tasks, client_for, query, titles):
    response = client_for(alice).get(f"/projects/{project.id}/tasks/?{query}")
    assert response.status_code == 200
    assert [t["title"] for t in response.json()["items"]] == titles
    assert response.json()["count"] == len(titles)
```

- The query string goes straight into the path, including a repeated `status` parameter. `TestClient` also takes `query_params={"status": ["todo", "in_progress"]}` if you prefer a dict.
- The titles are compared as a list, so each case also checks the order: `created_at` by default, or the `ordering` parameter from Part 5.
- `search=VIEWS` finds a match in the description and checks that the search ignores case.
- The paginated response wraps the tasks in `items`. Checking `count` as well makes sure the total that pagination reports agrees with the filtered list.

**Go deeper:** [Testing](../guide/testing.md#query-parameters)

## Comments and attachments

The last tests cover the object-level rules from Parts 4 and 6, and file uploads. Add them to the end of `tests/test_tasks.py`:

```python title="tests/test_tasks.py" hl_lines="16-17 22 25"
def test_only_author_can_edit_comment(alice, bob, task, client_for):
    comment = task.comments.create(author=bob, body="Looks good")
    url = f"/projects/{task.project_id}/tasks/{task.id}/comments/{comment.id}"

    response = client_for(alice).put(url, json={"body": "Changed"})
    assert response.status_code == 403

    response = client_for(alice).delete(url)  # the owner may delete it
    assert response.status_code == 204


def test_upload_attachment(alice, task, client_for, settings):
    file = SimpleUploadedFile("notes.txt", b"Remember the footer")
    response = client_for(alice).post(
        f"/projects/{task.project_id}/tasks/{task.id}/attachments",
        data={"name": "Meeting notes"},
        FILES={"file": file},
    )
    assert response.status_code == 201
    data = response.json()
    assert data["name"] == "Meeting notes"
    assert data["url"].startswith("http://testlocation/media/attachments/")

    attachment = task.attachments.get()
    assert (settings.MEDIA_ROOT / attachment.file.name).read_bytes() == b"Remember the footer"


def test_upload_rejects_file_type(alice, task, client_for):
    file = SimpleUploadedFile("setup.exe", b"MZ")
    response = client_for(alice).post(
        f"/projects/{task.project_id}/tasks/{task.id}/attachments", FILES={"file": file}
    )
    assert response.status_code == 422
    assert response.json()["detail"][0]["type"] == "file_type"
    assert not task.attachments.exists()


def test_delete_attachment(alice, bob, task, client_for, settings):
    file = SimpleUploadedFile("plan.pdf", b"%PDF-1.4")
    attachment = task.attachments.create(file=file, name="plan.pdf", uploaded_by=alice)
    url = f"/projects/{task.project_id}/tasks/{task.id}/attachments/{attachment.id}"

    response = client_for(bob).delete(url)
    assert response.status_code == 403

    response = client_for(alice).delete(url)
    assert response.status_code == 204
    assert not (settings.MEDIA_ROOT / attachment.file.name).exists()
```

- `SimpleUploadedFile` is Django's in-memory upload. It has a name, a size and content, which is all that `check_upload` and the `FileField` need.
- `data=` fills the form fields and `FILES=` the files, the two halves of the `multipart/form-data` request that `curl -F` sent in Part 6.
- `TestClient`'s fake request answers `build_absolute_uri()` with the host `testlocation`, so the resolver from Part 6 returns `http://testlocation/media/...`.
- The `settings` fixture gives the test the `MEDIA_ROOT` that `test_settings` set, so it can check the stored file on disk, and that `delete_attachment` removed it.

**Go deeper:** [Testing](../guide/testing.md#file-uploads)

## Running the tests

Run `pytest` from the folder with `manage.py`:

```console
$ pytest
============================= test session starts ==============================
...
django: version: 6.1.1, settings: taskflow.settings (from ini)
...
collected 31 items

tests/test_auth.py ....                                                  [ 12%]
tests/test_projects.py ......                                            [ 32%]
tests/test_tasks.py ....................                                 [ 96%]
tests/test_auth.py .                                                     [100%]

============================== 31 passed in 0.52s ==============================
```

`tests/test_auth.py` shows up twice because pytest-django runs the tests that don't use the database last. That's `test_missing_token`. Each parametrized case is a test of its own, so the 12 test functions in `test_tasks.py` make 20 tests.

`-k` picks tests by name, and `-v` lists them. Each parametrized case gets an id built from its parameters:

```console
$ pytest tests/test_tasks.py -k filter -v
...
collecting ... collected 20 items / 14 deselected / 6 selected

tests/test_tasks.py::test_filter_tasks[-titles0] PASSED                  [ 16%]
tests/test_tasks.py::test_filter_tasks[status=todo&status=in_progress-titles1] PASSED [ 33%]
tests/test_tasks.py::test_filter_tasks[assignee=bob&label=bug-titles2] PASSED [ 50%]
tests/test_tasks.py::test_filter_tasks[due_before=2026-10-05-titles3] PASSED [ 66%]
tests/test_tasks.py::test_filter_tasks[search=VIEWS-titles4] PASSED      [ 83%]
tests/test_tasks.py::test_filter_tasks[ordering=-priority-titles5] PASSED [100%]

======================= 6 passed, 14 deselected in 0.31s =======================
```

### When a check goes missing

A test suite proves its worth when someone breaks a rule by accident. Delete the author check from `update_comment` in `tasks/api.py`:

```python title="tasks/api.py"
    if comment.author != request.auth:
        raise HttpError(403, "Only the author can edit a comment")
```

Every other test still passes, and the endpoint still works for its author. Only the permission test notices:

```console
$ pytest
...
tests/test_tasks.py ................F...                                 [ 96%]
tests/test_auth.py .                                                     [100%]

=================================== FAILURES ===================================
______________________ test_only_author_can_edit_comment _______________________

alice = <User: alice>, bob = <User: bob>, task = <Task: Draft the sitemap>
client_for = <function client_for.<locals>.make_client at 0x7f6059af7a60>

    def test_only_author_can_edit_comment(alice, bob, task, client_for):
        comment = task.comments.create(author=bob, body="Looks good")
        url = f"/projects/{task.project_id}/tasks/{task.id}/comments/{comment.id}"
    
        response = client_for(alice).put(url, json={"body": "Changed"})
>       assert response.status_code == 403
E       assert 200 == 403
E        +  where 200 = <ninja.testing.client.NinjaResponse object at 0x7f6059b9a990>.status_code

tests/test_tasks.py:127: AssertionError
=========================== short test summary info ============================
FAILED tests/test_tasks.py::test_only_author_can_edit_comment - assert 200 ==...
========================= 1 failed, 30 passed in 0.59s =========================
```

pytest shows the fixtures the test received, the failing line, and the actual value: alice's edit of bob's comment returned `200`. Put the two lines back before you continue.

!!! tip
    `TestClient` skips `urls.py` and middleware to stay fast. To test the full stack, such as a custom middleware or the URL prefix, use Django's own `django.test.Client` with the `/api/...` URLs. Django Ninja views are normal Django views and work with it unchanged.

**Go deeper:** [Testing](../guide/testing.md#tips)

## Recap

- pytest-django needs `DJANGO_SETTINGS_MODULE` in `pytest.ini`. It creates a fresh test database and rolls back each test.
- Fixtures in `conftest.py` build users, a project with memberships, and a `client_for(user)` factory that sends a JWT with every request.
- `TestClient(api)` calls operations directly, with paths relative to the API. Auth, validation and error handling still run.
- Send bodies with `json=`, form fields with `data=`, files with `FILES=` and `SimpleUploadedFile`, and query strings in the path.
- `parametrize` turns a table of cases, such as status moves or filter queries, into separate tests.
- Point `MEDIA_ROOT` at `tmp_path` and use a fast password hasher, so tests stay clean and take under a second.

## Next

TaskFlow is complete and tested. In [Part 8: OpenAPI polish & versioning](part-8.md), you'll improve the generated docs with summaries, descriptions and examples, and run a second API version next to the first.
