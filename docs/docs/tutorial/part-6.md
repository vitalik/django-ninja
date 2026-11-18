# Part 6: File uploads & forms

Tasks often come with files: a design mockup, a screenshot of a bug, a PDF from the client. In this part you'll let members attach files to tasks. An upload is a `multipart/form-data` request instead of JSON, so you'll combine a file parameter with form fields, validate the file's size and type, store it with a plain `FileField`, and return an absolute URL for it.

!!! abstract "What you'll learn"
    - How to accept a file together with form fields using `File[...]` and `Form[...]`
    - How to validate an upload with a reusable annotated type, so errors come back as `422`
    - How to configure `MEDIA_ROOT` and serve uploaded files during development
    - How to build absolute URLs in a response with a resolver that reads the request
    - How to delete a file together with its database row, behind a permission check

    **Time:** about 15 minutes

## Storing files

An attachment belongs to a task and remembers who uploaded it. Add the model at the end of `tasks/models.py`:

```python title="tasks/models.py" hl_lines="3"
class Attachment(models.Model):
    task = models.ForeignKey(Task, related_name="attachments", on_delete=models.CASCADE)
    file = models.FileField(upload_to="attachments/%Y/%m/")
    name = models.CharField(max_length=200)
    uploaded_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, related_name="attachments", on_delete=models.CASCADE
    )
    uploaded_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.name
```

- `file` is a `FileField`, not an `ImageField`. `ImageField` needs Pillow, and attachments aren't only images.
- `upload_to` puts files in a folder per month, such as `attachments/2026/09/`. The database stores only that relative path. The file itself goes to the storage, which is the local disk by default.
- `name` is the display name. The client can choose it, or it defaults to the uploaded file's name.

```console
$ python manage.py makemigrations
Migrations for 'tasks':
  tasks/migrations/0005_attachment.py
    + Create model Attachment
$ python manage.py migrate
```

Django needs to know where to put uploads and under which URL to serve them. Add two settings below `STATIC_URL`:

```python title="taskflow/settings.py" hl_lines="4-5"
STATIC_URL = 'static/'

# User-uploaded files
MEDIA_URL = 'media/'
MEDIA_ROOT = BASE_DIR / 'media'
```

`runserver` doesn't serve `MEDIA_ROOT` on its own. Add Django's `static()` helper to the URLconf:

```python title="taskflow/urls.py" hl_lines="1-2 11"
from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import path

from .api import api

urlpatterns = [
    path("admin/", admin.site.urls),
    path("api/", api.urls),
] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
```

`static()` returns no URL patterns when `DEBUG` is off. In production, the web server or a storage service such as S3 serves the files. The `.gitignore` from Part 1 already excludes `media/`.

## Validating the upload

Django Ninja passes an uploaded file to your view as an `UploadedFile`, which is Django's own class. It already has a `name` and a `size`. Validation rules for it can live in the type, like any other Pydantic rule. Add the new imports and code to `tasks/schemas.py`:

```python title="tasks/schemas.py" hl_lines="2 5-6 12 21-26 29"
from datetime import date
from pathlib import Path
from typing import Annotated, Literal

from ninja import FilterLookup, FilterSchema, ModelSchema, Schema, UploadedFile
from pydantic import AfterValidator, Field, field_validator, model_validator
from pydantic_core import PydanticCustomError

from accounts.schemas import UserOut
from projects.schemas import LabelOut

from .models import Attachment, Comment, Priority, Task, TaskStatus

...


MAX_UPLOAD_SIZE = 5 * 1024 * 1024  # 5 MB
ALLOWED_EXTENSIONS = {".pdf", ".png", ".jpg", ".jpeg", ".txt", ".md"}


def check_upload(file: UploadedFile) -> UploadedFile:
    if file.size > MAX_UPLOAD_SIZE:
        raise PydanticCustomError("file_too_large", "Files can be at most 5 MB")
    if Path(file.name).suffix.lower() not in ALLOWED_EXTENSIONS:
        raise PydanticCustomError("file_type", "Only PDF, PNG, JPEG and text files are allowed")
    return file


AttachmentFile = Annotated[UploadedFile, AfterValidator(check_upload)]


class AttachmentIn(Schema):
    name: str = Field("", max_length=200)
```

- `check_upload` is a normal Pydantic validator. It runs after the file is parsed, and raises `PydanticCustomError` like the validators from Part 3, so a rejected file is a `422` with its own `type` and message.
- `AttachmentFile` bundles the type and its rules. Any endpoint that takes an attachment can use it, and the view only ever sees a valid file.
- The extension check uses the file name. The `content_type` of an upload comes from the client too, so neither proves what's inside the file. What they do prevent is storing, say, an `.html` file that your media server would then serve as a web page.
- Django has no size limit for uploaded files. `DATA_UPLOAD_MAX_MEMORY_SIZE` doesn't count them, and `FILE_UPLOAD_MAX_MEMORY_SIZE` only decides when Django switches from memory to a temporary file. The check runs after the whole file has arrived, so in production also cap the request size in the web server, such as `client_max_body_size` in nginx.
- `AttachmentIn` holds the form fields that come with the file. There is only one here, the optional display name.

**Go deeper:** [File Uploads](../guide/files.md#validation-and-metadata), [Errors & Exception Handling](../guide/errors.md#customizing-validation-errors)

## The upload endpoint

A file can't travel inside a JSON body, so the whole request is `multipart/form-data`: one part per form field, and one for the file. Add the imports and two endpoints to `tasks/api.py`:

```python title="tasks/api.py" hl_lines="2 11-13 38-39 42-44"
from django.shortcuts import get_object_or_404
from ninja import File, Form, PatchDict, Path, Query, Router, Status
from ninja.errors import HttpError
from ninja.pagination import CursorPagination, PageNumberPagination, paginate

from projects.models import Role
from projects.permissions import get_project_or_404

from .models import ALLOWED_TRANSITIONS, Priority, Task
from .schemas import (
    AttachmentFile,
    AttachmentIn,
    AttachmentOut,
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


@router.get("/{task_id}/attachments", response=list[AttachmentOut])
def list_attachments(request, project_id: Path[int], task_id: int):
    task = get_task_or_404(request.auth, project_id, task_id)
    return task.attachments.select_related("uploaded_by").order_by("id")


@router.post("/{task_id}/attachments", response={201: AttachmentOut})
def upload_attachment(
    request,
    project_id: Path[int],
    task_id: int,
    details: Form[AttachmentIn],
    file: File[AttachmentFile],
):
    task = get_task_or_404(request.auth, project_id, task_id)
    attachment = task.attachments.create(
        file=file, name=details.name or file.name, uploaded_by=request.auth
    )
    return Status(201, attachment)
```

- `Form[AttachmentIn]` reads the schema's fields from the form data, the same way `Query[TaskFilter]` read them from the query string in Part 5. The client sends a `name` field, not a `details` field.
- `File[AttachmentFile]` reads the `file` part from `request.FILES` and runs `check_upload`. With a `File` parameter present, Django Ninja documents the whole request body as `multipart/form-data`, and the interactive docs show a file picker.
- Passing the `UploadedFile` to `create()` is enough. The `FileField` saves it to the storage under `upload_to`, and the row gets the stored path.
- The file name comes from the client, but Django keeps only its last part. A file sent as `../../evil.pdf` is stored as `attachments/2026/09/evil.pdf`. If a file with the same name exists, the storage adds a random suffix, as in `footer_42rBBEz.png`, and the display name stays `footer.png`.
- Both endpoints start with `get_task_or_404` from Part 4, so only members of the project can list or upload files.

!!! note
    Django only fills `request.FILES` for `POST` requests. Django Ninja raises a `ConfigError` if you declare a `File` parameter on a `PUT` or `PATCH` operation, unless you add its compatibility middleware. The [File Uploads](../guide/files.md#requestfiles-with-put-and-patch) guide explains how.

**Go deeper:** [File Uploads](../guide/files.md#files-with-form-data-or-a-json-body), [Form Data](../guide/forms.md#grouping-parameters-into-a-schema)

## Absolute file URLs

A `FileField` listed in `Meta.fields` is serialized as its URL, such as `/media/attachments/2026/09/sitemap.pdf`. That's a path, not a URL. A mobile app or a frontend on another domain doesn't know which host to put in front of it. The request does, so `AttachmentOut` builds the full URL in a resolver:

```python title="tasks/schemas.py" hl_lines="3 10-11"
class AttachmentOut(ModelSchema):
    uploaded_by: UserOut
    url: str

    class Meta:
        model = Attachment
        fields = ["id", "name", "uploaded_at"]

    @staticmethod
    def resolve_url(obj, context):
        return context["request"].build_absolute_uri(obj.file.url)
```

- A resolver that takes a `context` argument receives `{"request": ..., "response_status": ...}` when the schema is used as a `response`. `build_absolute_uri()` adds the scheme and host of the current request.
- `url` is a new field that doesn't exist on the model. The model's `file` field isn't in `Meta.fields`, so the response has no relative path next to the absolute one.
- Declared fields come first in the output, so the keys are `uploaded_by`, `url`, then `id`, `name` and `uploaded_at`.

**Go deeper:** [Schemas: accessing context](../guide/schemas.md#accessing-context), [Schemas: files and images](../guide/schemas.md#files-and-images)

### Try it

Start `runserver` and set `TOKEN` to an access token for alice, as in Part 4. With any small PDF saved as `sitemap.pdf`, upload it to task 1. `curl -F` sends a `multipart/form-data` request, and `@` reads the file from disk:

```console
$ curl http://127.0.0.1:8000/api/projects/1/tasks/1/attachments \
    -H "Authorization: Bearer $TOKEN" \
    -F "name=Sitemap draft" \
    -F "file=@sitemap.pdf"
```

```json
{
    "uploaded_by": {
        "display_name": "Alice Martin",
        "id": 1,
        "username": "alice"
    },
    "url": "http://127.0.0.1:8000/media/attachments/2026/09/sitemap.pdf",
    "id": 1,
    "name": "Sitemap draft",
    "uploaded_at": "2026-09-28T11:12:57.878Z"
}
```

Don't set a `Content-Type` header yourself. `curl -F` sets it to `multipart/form-data` together with the boundary string that separates the parts. The URL works in the browser, and `curl -I` shows that Django serves it with the right type:

```console
$ curl -I http://127.0.0.1:8000/media/attachments/2026/09/sitemap.pdf
HTTP/1.1 200 OK
Date: Mon, 28 Sep 2026 11:13:36 GMT
Server: WSGIServer/0.2 CPython/3.12.13
Content-Type: application/pdf
Content-Length: 2025
Content-Disposition: inline; filename="sitemap.pdf"
...
```

The media URL needs no token. Anyone who has the link can download the file. That's fine for this tutorial, but for private files you'd return the file from an endpoint that checks permissions first, or use signed URLs from your storage service.

Now try a file type that isn't allowed, such as `-F "file=@setup.exe"`:

```json
{
    "detail": [
        {
            "type": "file_type",
            "loc": [
                "file",
                "file"
            ],
            "msg": "Only PDF, PNG, JPEG and text files are allowed"
        }
    ]
}
```

A 6 MB `scan.pdf` gets `"type": "file_too_large"` with the message `"Files can be at most 5 MB"`. Errors in the form fields and the file are collected together. A 201-character `name` with no file returns both:

```json
{
    "detail": [
        {
            "type": "string_too_long",
            "loc": [
                "form",
                "name"
            ],
            "msg": "String should have at most 200 characters",
            "ctx": {
                "max_length": 200
            }
        },
        {
            "type": "missing",
            "loc": [
                "file",
                "file"
            ],
            "msg": "Field required"
        }
    ]
}
```

The first item of `loc` is where the value was read from: `form` for form fields, `file` for files. A JSON body sent to this endpoint gets the same `missing` error for `file`.

## Deleting attachments

Deleting follows the rule from Part 4's comments, with one difference: the uploader can delete their own file, and so can the project's owners and admins. Add the endpoint to `tasks/api.py`:

```python title="tasks/api.py" hl_lines="5-7"
@router.delete("/{task_id}/attachments/{attachment_id}", response={204: None})
def delete_attachment(request, project_id: Path[int], task_id: int, attachment_id: int):
    task = get_task_or_404(request.auth, project_id, task_id)
    attachment = get_object_or_404(task.attachments, id=attachment_id)
    if attachment.uploaded_by != request.auth:
        get_project_or_404(request.auth, project_id, roles=[Role.OWNER, Role.ADMIN])
    attachment.file.delete(save=False)
    attachment.delete()
    return Status(204, None)
```

- `get_object_or_404(task.attachments, ...)` looks the attachment up within the task. An attachment id from another task is a `404`.
- For anyone but the uploader, `get_project_or_404` with `roles` does the role check, and raises a `403` for a plain member.
- Deleting the row doesn't delete the file. Django never removes files from the storage on its own, not even on a cascade. `attachment.file.delete(save=False)` removes it first. `save=False` skips saving the row, which is deleted on the next line anyway.

Bob is a member of the project, not an owner. Get a token for him (password `builder-42`) and put it in `BOB_TOKEN`. When he tries to delete alice's sitemap:

```console
$ curl -X DELETE http://127.0.0.1:8000/api/projects/1/tasks/1/attachments/1 -H "Authorization: Bearer $BOB_TOKEN"
```

```json
{
    "detail": "This needs the owner or admin role"
}
```

His own uploads, or alice deleting any attachment in her project, return `204` and remove the file from `media/`. Files deleted with the whole task, by the cascade, stay on disk. Cleaning those up takes a periodic job or a `post_delete` signal.

**Go deeper:** [Authentication](../guide/authentication.md#authorization-and-permissions)

## Recap

- A `File[...]` parameter makes the request `multipart/form-data`. Combine it with `Form[Schema]` to read the other fields, which are validated like a JSON body.
- `Annotated[UploadedFile, AfterValidator(...)]` puts size and type rules into a reusable type. A bad file is a `422` with `loc` `["file", ...]`, next to any form errors.
- Store uploads with a `FileField` and `MEDIA_ROOT`, and serve them with `static()` in development only.
- A resolver with a `context` argument can read the request, and `build_absolute_uri()` turns a file's path into a full URL.
- Delete the stored file together with the row. Django won't do it for you.

## Next

TaskFlow now has most of its features, and each part checked them by hand. In [Part 7: Testing](part-7.md), you'll turn those checks into a pytest suite with Django Ninja's `TestClient`, covering CRUD, validation, permissions, filters and uploads.
