# File uploads

Handling files are no different from other parameters.

```python hl_lines="1 2 5"
from ninja import NinjaAPI, File
from ninja.files import UploadedFile

@api.post("/upload")
def upload(request, file: File[UploadedFile]):
    data = file.read()
    return {'name': file.name, 'len': len(data)}
```


`UploadedFile` is an alias to [Django's UploadFile](https://docs.djangoproject.com/en/stable/ref/files/uploads/#django.core.files.uploadedfile.UploadedFile) and has all the methods and attributes to access the uploaded file:

 - read()
 - multiple_chunks(chunk_size=None)
 - chunks(chunk_size=None)
 - name
 - size
 - content_type
 - content_type_extra
 - charset
 - etc.

## Uploading array of files

To **upload several files** at the same time, just declare a `List` of `UploadedFile`:


```python hl_lines="1 6"
from typing import List
from ninja import NinjaAPI, File
from ninja.files import UploadedFile

@api.post("/upload-many")
def upload_many(request, files: File[List[UploadedFile]]):
    return [f.name for f in files]
```

## Uploading files with extra fields

Note: The HTTP protocol does not allow you to send files in `application/json` format by default (unless you encode it somehow to JSON on client side)

To send files along with some extra attributes, you need to send bodies with `multipart/form-data` encoding. You can do it by simply marking fields with `Form`:

```python hl_lines="14"
from ninja import NinjaAPI, Schema, UploadedFile, Form, File
from datetime import date

api = NinjaAPI()


class UserDetails(Schema):
    first_name: str
    last_name: str
    birthdate: date


@api.post('/users')
def create_user(request, details: Form[UserDetails], file: File[UploadedFile]):
    return [details.dict(), file.name]

```

Note: in this case all fields should be send as form fields

You can as well send payload in single field as JSON - just remove the Form mark from:

```python
@api.post('/users')
def create_user(request, details: UserDetails, file: File[UploadedFile]):
    return [details.dict(), file.name]

```

this will expect from the client side to send data as `multipart/form-data with 2 fields:
  
  - details: JSON as string
  - file: file


### List of files with extra info

```python
@api.post('/users')
def create_user(request, details: Form[UserDetails], files: File[list[UploadedFile]]):
    return [details.dict(), [f.name for f in files]]
```

### Optional file input

If you would like the file input to be optional, all that you have to do is to pass `None` to the `File` type, like so:

```python
@api.post('/users')
def create_user(request, details: Form[UserDetails], avatar: File[UploadedFile] = None):
    user = add_user_to_database(details)
    if avatar is not None:
        set_user_avatar(user)
```
