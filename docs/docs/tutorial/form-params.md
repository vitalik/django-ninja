# Form data

**Django Ninja** also allows you to parse and validate `request.POST` data (aka `application x-www-form-urlencoded` or `multipart/form-data`)

Here is a quick example:

```Python hl_lines="1 4"
from ninja import NinjaAPI, Form

@api.post("/login")
def login(request, username: str = Form(...), password: str = Form(...)):
    return {'username': username, 'password': '*****'}
```

Note the following:

1) You need to import `Form` mark from ninja
```Python
from ninja import Form
```

2) Use `Form` as default value for your parameter:
```Python
username: str = Form(...)
```

