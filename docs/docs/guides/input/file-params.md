# File uploads

Handling files are no different from other parameters.

```Python hl_lines="1 2 5"
from ninja import NinjaAPI, File
from ninja.files import UploadedFile

@api.post("/upload")
def upload(request, file: UploadedFile = File(...)):
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
 - etc.

## Uploading array of files

To **upload several files** at the same time, just declare a `List` of `UploadFile`:


```Python hl_lines="1 6"
from typing import List
from ninja import NinjaAPI, File
from ninja.files import UploadedFile

@api.post("/upload-many")
def upload_many(request, files: List[UploadedFile] = File(...)):
    return [f.name for f in files]
```

## Uploading files with extra fields

Note: HTTP protocol does not allow you to send files in application/json format by default (unless you encode it somehow to JSON on client side)

To send files along with some extra attributes you need to send bodies in multipart/form-data encoding. You can do it by simply marking fields with `Form`:

```Python hl_lines="14"
from ninja import NinjaAPI, Schema, UploadedFile, Form, File
from datetime import date

api = NinjaAPI()


class UserDetails(Schema):
    first_name: str
    last_name: str
    birthdate: date


@api.post('/user')
def create_user(request, details: UserDetails = Form(...), file: UploadedFile = File(...)):
    return [details.dict(), file.name]

```

Note: in this case all fields should be send as form fields

You can as well send payload in single field as JSON - just remove the Form mark from:

```Python
@api.post('/user')
def create_user(request, details: UserDetails, file: UploadedFile = File(...)):
    return [details.dict(), file.name]

```

this will expect from client side to send data as multipart/form-data with 2 fields:
  
  - details: Json as string
  - file: file
