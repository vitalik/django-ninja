# Response Schema

**Django Ninja** allows you define schema of your responses both for validation and documentation purposes.

Let's check the following example. Imagine you need to create an api operation that creates a user. The **input** parameter would be **username+password**, but **output** of this operation should be **id+username** (**without** the password).

Let's create input schema:

```Python hl_lines="3 5"
from ninja import Schema

class UserIn(Schema):
    username: str
    password: str


@api.post("/users/")
def create_user(request, data: UserIn):
    user = User(username=data.username) # User is django auth.User
    user.set_password(data.password)
    user.save()
    # ... return ?

```

Now let's define output schema, and pass it as `response` argument to @api.post:

```Python hl_lines="8 9 10 13 18"
from ninja import Schema

class UserIn(Schema):
    username: str
    password: str


class UserOut(Schema):
    id: int
    username: str


@api.post("/users/", response=UserOut)
def create_user(request, data: UserIn):
    user = User(username=data.username)
    user.set_password(data.password)
    user.save()
    return user
```

Django Ninja will use this `response` schema to:

 - Convert the output data to declared schema.
 - Validate the data.
 - Add OpenAPI schema definition.
 - Will be used by the automatic documentation systems.
 - And (most importantly) **will limit the output data** to fields only defined in schema.


## Nested objects

There is also often a need to return responses with some nested/child objects

Let's check the following example - imagine we have a `Task` django model with `User` ForeignKey:

```Python  hl_lines="6"
from django.db import models

class Task(models.Model):
    title = models.CharField(max_length=200)
    is_completed = models.BooleanField(default=False)
    owner: models.ForeignKey("auth.User", null=True, blank=True)
```

Now let's output all task and for each task output some fields about the user

```Python  hl_lines="13 16"
from typing import List
from ninja import Schema

class UserSchema(Schema):
    id: int
    first_name: str
    last_name: str

class TaskSchema(Schema):
    id: int
    title: str
    is_completed: bool
    owner: UserSchema = None  # ! None - to mark it as optional


@api.get("/tasks", response=List[TaskSchema])
def tasks(request):
    queryset = Task.objects.all()
    return list(queryset)
```

If you execute this operation you should  get a response like this:

```JSON  hl_lines="6 7 8 9 16"
[
    {
        "id": 1, 
        "title": "Task 1",
        "is_completed": false,
        "owner": {
            "id": 1,
            "first_name": "John",
            "last_name": "Doe",
        }
    },
    {
        "id": 2, 
        "title": "Task 2",
        "is_completed": false,
        "owner": null
    },
]
```

## Returning querysets

In the previous example we specifically converted a queryset into a list (and executing SQL query during evaluation).

But you can avoid it and return a queryset as a result and it will be automatically evaluated to List:

```Python hl_lines="3"
@api.get("/tasks", response=List[TaskSchema])
def tasks(request):
    return Task.objects.all()
```

### Note about async mode

If your opertation is async [async-support](https://django-ninja.rest-framework.com/async-support) this example will not work

```Python hl_lines="2 3"
@api.get("/tasks", response=List[TaskSchema])
async def tasks(request):
    return Task.objects.all()
```
