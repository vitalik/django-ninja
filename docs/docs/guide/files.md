# File Uploads

To receive an uploaded file, annotate a parameter with `UploadedFile`. Django
Ninja reads it from `request.FILES`, and — because a file can only travel
over HTTP as `multipart/form-data` — automatically switches the operation's
request encoding to `multipart/form-data` the moment it sees a `File`
parameter (combined with [`Form`](forms.md) fields or a JSON body, if there
are any).

## Basic usage

```python hl_lines="1 7"
from ninja import NinjaAPI, UploadedFile

api = NinjaAPI()


@api.post("/upload")
def upload(request, file: UploadedFile):
    data = file.read()
    return {"name": file.name, "len": len(data)}
```

You don't need to mark the parameter with `File(...)` — Django Ninja
recognizes the `UploadedFile` type on its own and treats it as a file
parameter automatically. Marking it explicitly with `File` works exactly the
same way and is useful once you need [validation constraints](#validation-and-metadata):

```python hl_lines="1 7"
from ninja import File, NinjaAPI, UploadedFile

api = NinjaAPI()


@api.post("/upload")
def upload(request, file: UploadedFile = File(...)):
    data = file.read()
    return {"name": file.name, "len": len(data)}
```

`UploadedFile` is Django's own [`UploadedFile`](https://docs.djangoproject.com/en/stable/ref/files/uploads/#django.core.files.uploadedfile.UploadedFile)
(Django Ninja re-exports it so Pydantic knows how to validate it), so it has
all of the usual attributes and methods:

- `read(size=None)`
- `multiple_chunks(chunk_size=None)`
- `chunks(chunk_size=None)`
- `name`
- `size`
- `content_type`
- `content_type_extra`
- `charset`

## Multiple files

Declare a `list` of `UploadedFile` to accept several files under the same
field name:

```python hl_lines="7"
from ninja import NinjaAPI, UploadedFile

api = NinjaAPI()


@api.post("/upload-many")
def upload_many(request, files: list[UploadedFile]):
    return [f.name for f in files]
```

A client sends this as several `multipart/form-data` parts that all share the
`files` field name. `set` and `tuple` annotations work the same way.

You can also just declare several separate `UploadedFile` parameters — each
one reads from its own field name (`file1`, `file2`, ...), and you can mix
single files and lists of files on the same operation:

```python hl_lines="7"
from ninja import NinjaAPI, UploadedFile

api = NinjaAPI()


@api.post("/upload-both")
def upload_both(request, file: UploadedFile, extra: list[UploadedFile]):
    return {"file": file.name, "extra": [f.name for f in extra]}
```

## Optional files

Give the parameter a `File(None)` default (and a `| None` annotation) to make
it optional. A bare `None` default doesn't work here, since the automatic
`UploadedFile` → `File` detection only kicks in when the annotation is
exactly `UploadedFile`, not `UploadedFile | None`:

```python hl_lines="1 7"
from ninja import File, NinjaAPI, UploadedFile

api = NinjaAPI()


@api.post("/upload-optional")
def upload_optional(request, file: UploadedFile | None = File(None)):
    if file is None:
        return {"uploaded": False}
    return {"uploaded": True, "name": file.name}
```

## Validation and metadata

`File()` accepts the same arguments as [`Form()`](forms.md#validation-constraints):
`gt`, `ge`, `lt`, `le`, `min_length`, `max_length`, `pattern`, plus `alias`,
`title`, `description`, `example`/`examples`, `deprecated` and
`include_in_schema` for the generated OpenAPI schema.

`min_length`/`max_length` are most useful on a list of files, where they
constrain how many files must be sent:

```python hl_lines="8"
from ninja import File, NinjaAPI, UploadedFile

api = NinjaAPI()


@api.post("/upload-gallery")
def upload_gallery(
    request, images: list[UploadedFile] = File(..., min_length=1, max_length=5)
):
    return [f.name for f in images]
```

Use `alias` when the multipart field name isn't a valid Python identifier:

```python hl_lines="7"
from ninja import File, NinjaAPI, UploadedFile

api = NinjaAPI()


@api.post("/upload-legacy")
def upload_legacy(request, file: UploadedFile = File(..., alias="user-file")):
    return {"name": file.name}
```

The same shorthand available for the other parameter sources works here too —
`File[UploadedFile]` is equivalent to `UploadedFile = File(...)`:

```python hl_lines="1 7"
from ninja import File, NinjaAPI, UploadedFile

api = NinjaAPI()


@api.post("/upload")
def upload(request, file: File[UploadedFile]):
    return {"name": file.name}
```

## Files with form data or a JSON body

Because the HTTP protocol has no way to put binary files inside
`application/json`, sending files alongside other data means sending
everything as `multipart/form-data`. Django Ninja does this switch for you
automatically whenever an operation has at least one `File` parameter — you
don't need to configure anything.

=== "Form fields"

    Mark the extra fields with [`Form`](forms.md), individually or grouped in
    a `Schema`. Each field becomes its own part of the `multipart/form-data`
    request:

    ```python hl_lines="15"
    from datetime import date

    from ninja import File, Form, NinjaAPI, Schema, UploadedFile

    api = NinjaAPI()


    class UserDetails(Schema):
        first_name: str
        last_name: str
        birth_date: date


    @api.post("/users")
    def create_user(request, details: Form[UserDetails], file: UploadedFile = File(...)):
        return [details.dict(), file.name]
    ```

    The client sends `first_name`, `last_name`, `birth_date` and `file` as four
    separate `multipart/form-data` parts.

=== "JSON body"

    Leave the schema as a plain (`Body`-like) parameter instead, and it's sent
    as a *single* multipart field whose value is the JSON-encoded object:

    ```python hl_lines="15"
    from datetime import date

    from ninja import File, NinjaAPI, Schema, UploadedFile

    api = NinjaAPI()


    class UserDetails(Schema):
        first_name: str
        last_name: str
        birth_date: date


    @api.post("/users")
    def create_user(request, details: UserDetails, file: UploadedFile = File(...)):
        return [details.dict(), file.name]
    ```

    The client now sends exactly two `multipart/form-data` parts: `details`
    (the object, serialized to a JSON string) and `file`.

Both styles combine with `list[UploadedFile]` the same way — replace `file`
above with `images: list[UploadedFile]` to accept a `Schema` plus a gallery of
files in one request.

!!! tip
    Path and query parameters can still be declared on the same operation —
    Django Ninja resolves each parameter from its own source regardless of
    how many `File`/`Form`/`Body` parameters are mixed in.

## request.FILES with PUT and PATCH

Django's `request.FILES` is [only populated for `POST` requests by
default](https://groups.google.com/g/django-users/c/BeBKj_6qNsc) — a long
standing Django behavior, not specific to Django Ninja. This means a `PUT` or
`PATCH` operation that declares a `File` parameter would never actually
receive the file, since `request.FILES` stays empty.

Django Ninja detects this at operation-registration time and raises
`ninja.errors.ConfigError` immediately instead of letting the endpoint fail
silently at request time:

```python
@api.patch("/upload")  # raises ConfigError as soon as this module is imported
def upload(request, file: UploadedFile):
    ...
```

To fix it, add Django Ninja's compatibility middleware to `MIDDLEWARE`. It
manually parses `multipart/form-data` for the affected methods and populates
`request.FILES` before your view runs:

```python
MIDDLEWARE = [
    # ... your existing middleware ...
    "ninja.compatibility.files.fix_request_files_middleware",
]
```

By default the middleware (and the `ConfigError` check) applies to `PUT`,
`PATCH` and `DELETE`. Override which methods it covers with the
`NINJA_FIX_REQUEST_FILES_METHODS` setting:

```python
NINJA_FIX_REQUEST_FILES_METHODS = {"PUT", "PATCH"}
```

!!! note
    The middleware only touches requests it needs to — it leaves normal
    `POST` requests, requests with an `application/json` body, and any method
    not listed in `NINJA_FIX_REQUEST_FILES_METHODS` completely alone.

## Notes

- File uploads are still bound by Django's own upload settings —
  [`DATA_UPLOAD_MAX_MEMORY_SIZE`](https://docs.djangoproject.com/en/stable/ref/settings/#data-upload-max-memory-size),
  [`FILE_UPLOAD_MAX_MEMORY_SIZE`](https://docs.djangoproject.com/en/stable/ref/settings/#file-upload-max-memory-size)
  and [`FILE_UPLOAD_PERMISSIONS`](https://docs.djangoproject.com/en/stable/ref/settings/#file-upload-permissions)
  apply the same way they would in a plain Django view. Django Ninja doesn't
  add a size limit of its own on top of these.
- Uploaded files behave like any other parameter in tests — see
  [Testing](testing.md) for how `TestClient` sends `FILES`.
