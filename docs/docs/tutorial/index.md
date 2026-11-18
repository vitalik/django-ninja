# Tutorial

This tutorial builds one realistic API from start to finish: **TaskFlow**, a task tracker for teams. Users sign up, create projects, invite members with roles, and track tasks with assignees, labels, statuses, due dates, comments and file attachments. Each part adds a feature to the same codebase and shows the Django Ninja tools that make it work.

## What you'll build

By the end of Part 8, TaskFlow has these endpoints:

| Method | URL | What it does |
| --- | --- | --- |
| `POST` | `/api/auth/signup` | Create an account |
| `POST` | `/api/auth/token`, `/api/auth/refresh` | Get and refresh JWT access tokens |
| `GET`, `POST` | `/api/projects/` | List your projects, create one |
| `GET`, `PUT`, `DELETE` | `/api/projects/{project_id}` | Read, update and delete a project |
| `POST` | `/api/projects/{project_id}/labels` | Add a label to a project |
| `GET`, `POST` | `/api/projects/{project_id}/members` | List and add members |
| `GET`, `POST` | `/api/projects/{project_id}/tasks/` | Filter, search, sort and paginate tasks, create one |
| `GET`, `PATCH` | `/api/projects/{project_id}/tasks/{task_id}` | Read a task, update part of it |
| `POST` | `/api/projects/{project_id}/tasks/{task_id}/status` | Move a task through its workflow |
| `GET`, `POST` | `/api/projects/{project_id}/tasks/{task_id}/comments` | List comments with a cursor, add one |
| `PUT`, `DELETE` | `/api/projects/{project_id}/tasks/{task_id}/comments/{comment_id}` | Edit or delete a comment |
| `GET`, `POST` | `/api/projects/{project_id}/tasks/{task_id}/attachments` | List attachments, upload a file |
| `DELETE` | `/api/projects/{project_id}/tasks/{task_id}/attachments/{attachment_id}` | Delete an attachment |

Every endpoint except the auth ones needs a token, and users only ever see the projects they're members of. A second version of the API runs next to the first at `/api/v2/`, and a pytest suite covers the rules that matter.

## Before you start

- You know Django: projects, apps, models, migrations and settings. The tutorial doesn't explain those. It focuses on the Django Ninja parts.
- You've done the [Quick Start](../quickstart/index.md), so `NinjaAPI`, schemas and the interactive docs are familiar.
- You have Python 3.12 or newer. The code uses modern type hints such as `int | None` and `list[int]`.

The only packages TaskFlow needs are Django and Django Ninja:

```console
pip install django django-ninja
```

Everything else, including JSON Web Tokens, is written with the standard library. Part 7 adds pytest and pytest-django as development tools. The database is SQLite, and all views are synchronous.

## How the parts work

- Each part starts with a **What you'll learn** box and takes about 15 minutes to read and type.
- Each part builds on the code of the one before, so work through them in order. Changed files are shown in full, or as excerpts with `...` where the rest of the file stays the same.
- The example requests and responses are real output. If you start from an empty database, as Part 2 suggests, your ids will match the ones on the pages.
- **Go deeper** links at the end of each section point to the [Guide](../guide/index.md) page that covers the feature in full.

## The parts

1. [Project setup & layout](part-1.md): one router per app, schemas from models, and task URLs nested under projects.
2. [Relations & computed fields](part-2.md): assignees and labels as nested output, computed and annotated fields, and fewer queries.
3. [Validation & workflows](part-3.md): status and priority choices, field and model validators, `PATCH` updates and status transitions.
4. [Auth & permissions](part-4.md): JWT tokens from scratch, project memberships with roles, and object-level rules for comments.
5. [Filtering, search, ordering & pagination](part-5.md): a `FilterSchema` for tasks, safe sort orders, and page-number and cursor pagination.
6. [File uploads & forms](part-6.md): multipart uploads with form fields, file validation, media files and absolute URLs.
7. [Testing](part-7.md): a pytest suite with fixtures and `TestClient`, covering validation, permissions, filters and uploads.
8. [OpenAPI polish & versioning](part-8.md): descriptions, examples and deprecations in the docs, and a version 2 next to version 1.

Ready? Start with [Part 1: Project setup & layout](part-1.md).
