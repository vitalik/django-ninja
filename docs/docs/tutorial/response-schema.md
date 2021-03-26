# Response Schema

**Django Ninja** allows you to define the schema of your responses both for validation and documentation purposes.

Imagine you need to create an API operation that creates a user. The **input** parameter would be **username+password**, but **output** of this operation should be **id+username** (**without** the password).

Let's create the input schema:

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

Now let's define the output schema, and pass it as a `response` argument to the `@api.post` decorator:

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

 - convert the output data to declared schema
 - validate the data
 - add an OpenAPI schema definition
 - it will be used by the automatic documentation systems
 - and, most importantly, it **will limit the output data** only to the fields only defined in the schema.


## Nested objects

There is also often a need to return responses with some nested/child objects.

Imagine we have a `Task` Django model with a `User` ForeignKey:

```Python  hl_lines="6"
from django.db import models

class Task(models.Model):
    title = models.CharField(max_length=200)
    is_completed = models.BooleanField(default=False)
    owner = models.ForeignKey("auth.User", null=True, blank=True)
```

Now let's output all tasks, and for each task, output some fields about the user.

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

If you execute this operation, you should get a response like this:

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

In the previous example we specifically converted a queryset into a list (and executed the SQL query during evaluation).

You can avoid that and return a queryset as a result, and it will be automatically evaluated to List:

```Python hl_lines="3"
@api.get("/tasks", response=List[TaskSchema])
def tasks(request):
    return Task.objects.all()
```

### Note about async mode

If your operation is async [async-support](https://django-ninja.rest-framework.com/async-support), this example will not work.

```Python hl_lines="2 3"
@api.get("/tasks", response=List[TaskSchema])
async def tasks(request):
    return Task.objects.all()
```


## FileField and ImageField

**Django Ninja** by default converts files and images (declared with `FileField` or `ImageField`) to `string` URL's.

An example:

```Python hl_lines="3"
class Picture(models.Model):
    title = models.CharField(max_length=100)
    image = models.ImageField(upload_to='images')
```

If you need to output to response image field, declare a schema for it as follows:
```Python hl_lines="3"
class PictureSchema(Schema):
    title: str
    image: str
```

Once you output this to a response, the URL will be automatically generated for each object:
```JSON
{
    "title": "Zebra",
    "image": "/static/images/zebra.jpg"
}
```

## Multiple Response Schemas


Sometimes you need to define more than response schemas.
In case of authentication, for example, you can return:

 - **200** successful -> token
 - **401** -> Unauthorized
 - **402** -> Payment required
 - etc..

In fact, the [OpenAPI specification](https://swagger.io/docs/specification/describing-responses/) allows you to pass multiple response schemas.


You can pass to a `response` argument a dictionary where:

 - key is a response code
 - value is a schema for that code

Also, when you return the result - you have to also pass a status code to tell Django Ninja which schema should be used for validation and serialization.


An example:

```Python hl_lines="9 12 14 16"
class Token(Schema):
    token: str
    expires: date

class Message(Schema):
    message: str


@api.post('/login', response={200: Token, 401: Message, 402: Message})
def login(request, payload: Auth):
    if auth_not_valid:
        return 401, {'message': 'Unauthorized'}
    if negative_balance:
        return 402, {'message': 'Insufficient balance amount. Please proceed to a payment page.'}
    return 200, {'token': xxx, ...}
```

## Multiple response codes

In the previous example you saw that we basically repeated the `Message` schema twice:

```
...401: Message, 402: Message}
```

To avoid this duplication you can use multiple response codes for a schema:

```Python hl_lines="2 5 8 10"
...
from ninja.responses import codes_4xx


@api.post('/login', response={200: Token, codes_4xx: Message})
def login(request, payload: Auth):
    if auth_not_valid:
        return 401, {'message': 'Unauthorized'}
    if negative_balance:
        return 402, {'message': 'Insufficient balance amount. Please proceed to a payment page.'}
    return 200, {'token': xxx, ...}
```

Django Ninja comes with the following HTTP codes:

```Python
from ninja.responses import codes_1xx
from ninja.responses import codes_2xx
from ninja.responses import codes_3xx
from ninja.responses import codes_4xx
from ninja.responses import codes_5xx
```

You can also create your own range using a `frozenset`:

```Python
my_codes = frozenset({416, 418, 425, 429, 451})
...
@api.post('/login', response={200: Token, my_codes: Message})
...
```


## Empty responses

Some responses, such as `204 No Content`, have no body. To indicate the response body is empty mark `response` argument with `None` instead of Schema:

```Python hl_lines="1 3"
@api.post("/no_content", response={204: None})
def no_content(request):
    return 204, None
```


## Self-referencing schemes

Sometimes you need to create a schema that has reference to itself, or tree-structure objects.

To do that you need:

 - set a type of you schema in quotes
 - use `update_forward_refs` method to apply self referencing types

```Python hl_lines="3 6"
class Organization(Schema):
    title: str
    part_of: 'Organization' = None     #!! note the type in quotes here !!


Organization.update_forward_refs()  # !!! this is important


@api.get('/organizations', response=List[Organization])
def list_organizations(request):
    ...
```
