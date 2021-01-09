# File uploads

Handling files are no different from other parameters. Let's check this example:

```Python hl_lines="1 2 5"
from ninja import NinjaAPI, File
from ninja.files import UploadedFile

@api.post("/upload")
def upload(request, file: UploadedFile = File(...)):
    data = file.read()
    return {'name': file.name, 'len': len(data)}
```


Note about `UploadedFile`.

Basically it's an alias to [Django's UploadFile](https://docs.djangoproject.com/en/3.1/ref/files/uploads/) and has all the methods and attributes to access the uploaded file:

 - read()
 - multiple_chunks(chunk_size=None)
 - chunks(chunk_size=None)
 - name
 - size
 - content_type
 - etc.


It's possible to **upload several files** at the same time.

To use that, declare a `List` of  `UploadFile`:


```Python hl_lines="1 6"
from typing import List
from ninja import NinjaAPI, File
from ninja.files import UploadedFile

@api.post("/upload-many")
def upload_many(request, files: List[UploadedFile] = File(...)):
    return [f.name for f in files]
```