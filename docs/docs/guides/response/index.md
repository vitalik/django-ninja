# Response Schema

**Django Ninja** allows you to define the schema of your responses both for validation and documentation purposes.

Imagine you need to create an API operation that creates a user. The **input** parameter would be **username+password**, but **output** of this operation should be **id+username** (**without** the password).

Let's create the input schema:

```python hl_lines="3 5"
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

```python hl_lines="8 9 10 13 18"
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

**Django Ninja** will use this `response` schema to:

- convert the output data to declared schema
- validate the data
- add an OpenAPI schema definition
- it will be used by the automatic documentation systems
- and, most importantly, it **will limit the output data** only to the fields only defined in the schema.

## Nested objects

There is also often a need to return responses with some nested/child objects.

Imagine we have a `Task` Django model with a `User` ForeignKey:

```python hl_lines="6"
from django.db import models

class Task(models.Model):
    title = models.CharField(max_length=200)
    is_completed = models.BooleanField(default=False)
    owner = models.ForeignKey("auth.User", null=True, blank=True)
```

Now let's output all tasks, and for each task, output some fields about the user.

```python hl_lines="13 16"
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
    queryset = Task.objects.select_related("owner")
    return list(queryset)
```

If you execute this operation, you should get a response like this:

```JSON hl_lines="6 7 8 9 16"
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

## Aliases

Instead of a nested response, you may want to just flatten the response output.
The Ninja `Schema` object extends Pydantic's `Field(..., alias="")` format to
work with dotted responses.

Using the models from above, let's make a schema that just includes the task
owner's first name inline, and also uses `completed` rather than `is_completed`:

```python hl_lines="1 7-9"
from ninja import Field, Schema


class TaskSchema(Schema):
    id: int
    title: str
    # The first Field param is the default, use ... for required fields.
    completed: bool = Field(..., alias="is_completed")
    owner_first_name: str = Field(None, alias="owner.first_name")
```

Aliases also support django template syntax variables access:

```python hl_lines="2"
class TaskSchema(Schema):
    last_message: str = Field(None, alias="message_set.0.text")
```

```python hl_lines="3"
class TaskSchema(Schema):
    type: str = Field(None)
    type_display: str = Field(None, alias="get_type_display") # callable will be executed
```

## Resolvers

You can also create calculated fields via resolve methods based on the field
name.

The method must accept a single argument, which will be the object the schema
is resolving against.

When creating a resolver as a standard method, `self` gives you access to other
validated and formatted attributes in the schema.

```python hl_lines="5 7-11"
class TaskSchema(Schema):
    id: int
    title: str
    is_completed: bool
    owner: Optional[str] = None
    lower_title: str

    @staticmethod
    def resolve_owner(obj):
        if not obj.owner:
            return
        return f"{obj.owner.first_name} {obj.owner.last_name}"

    def resolve_lower_title(self, obj):
        return self.title.lower()
```

### Accessing extra context

Pydantic v2 allows you to process an extra context that is passed to the serializer. In the following example you can have resolver that gets request object from passed `context` argument:

```python hl_lines="6"
class Data(Schema):
    a: int
    path: str = ""

    @staticmethod
    def resolve_path(obj, context):
        request = context["request"]
        return request.path
```

if you use this schema for incoming requests - the `request` object will be automatically passed to context.

You can as well pass your own context:

```python
data = Data.model_validate({'some': 1}, context={'request': MyRequest()})
```

## Returning querysets

In the previous example we specifically converted a queryset into a list (and executed the SQL query during evaluation).

You can avoid that and return a queryset as a result, and it will be automatically evaluated to List:

```python hl_lines="3"
@api.get("/tasks", response=List[TaskSchema])
def tasks(request):
    return Task.objects.all()
```

!!! warning

    If your operation is async, this example will not work because the ORM query needs to be called safely.

    ```python hl_lines="2"
    @api.get("/tasks", response=List[TaskSchema])
    async def tasks(request):
        return Task.objects.all()
    ```

    See the [async support](../async-support.md#using-orm) guide for more information.

## FileField and ImageField

**Django Ninja** by default converts files and images (declared with `FileField` or `ImageField`) to `string` URL's.

An example:

```python hl_lines="3"
class Picture(models.Model):
    title = models.CharField(max_length=100)
    image = models.ImageField(upload_to='images')
```

If you need to output to response image field, declare a schema for it as follows:

```python hl_lines="3"
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
- **403** -> Forbidden
- etc..

In fact, the [OpenAPI specification](https://swagger.io/docs/specification/describing-responses/) allows you to pass multiple response schemas.

You can pass to a `response` argument a dictionary where:

- key is a response code
- value is a schema for that code

Also, when you return the result - you have to also pass a status code to tell **Django Ninja** which schema should be used for validation and serialization.

An example:

```python hl_lines="9 12 14 16"
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

```python hl_lines="2 5 8 10"
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

**Django Ninja** comes with the following HTTP codes:

```python
from ninja.responses import codes_1xx
from ninja.responses import codes_2xx
from ninja.responses import codes_3xx
from ninja.responses import codes_4xx
from ninja.responses import codes_5xx
```

You can also create your own range using a `frozenset`:

```python
my_codes = frozenset({416, 418, 425, 429, 451})

@api.post('/login', response={200: Token, my_codes: Message})
def login(request, payload: Auth):
    ...
```

## Empty responses

Some responses, such as [204 No Content](https://developer.mozilla.org/en-US/docs/Web/HTTP/Status/204), have no body.
To indicate the response body is empty mark `response` argument with `None` instead of Schema:

```python hl_lines="1 3"
@api.post("/no_content", response={204: None})
def no_content(request):
    return 204, None
```

## Error responses

Check [Handling errors](../errors.md) for more information.

## Self-referencing schemes

Sometimes you need to create a schema that has reference to itself, or tree-structure objects.

To do that you need:

- set a type of your schema in quotes
- use `model_rebuild` method to apply self referencing types

```python hl_lines="3 6"
class Organization(Schema):
    title: str
    part_of: 'Organization' = None     #!! note the type in quotes here !!


Organization.model_rebuild()  # !!! this is important


@api.get('/organizations', response=List[Organization])
def list_organizations(request):
    ...
```

## Self-referencing schemes from `create_schema()`

To be able to use the method `model_rebuild()` from a schema generated via `create_schema()`,
the "name" of the class needs to be in our namespace. In this case it is very important to pass
the `name` parameter to `create_schema()`

```python hl_lines="3"
UserSchema = create_schema(
    User,
    name='UserSchema',  # !!! this is important for model_rebuild()
    fields=['id', 'username']
    custom_fields=[
        ('manager', 'UserSchema', None),
    ]
)
UserSchema.model_rebuild()
```

## Serializing Outside of Views

Serialization of your objects can be done directly in code through the use of
the `.from_orm()` method on the schema object.

Consider the following model:

```python
class Person(models.Model):
    name = models.CharField(max_length=50)
```

Which can be accessed using this schema:

```python
class PersonSchema(Schema):
    name: str
```

Direct serialization can be performed using the `.from_orm()` method on the
schema. Once you have an instance of the schema object, the `.dict()` and
`.json()` methods allow you to get at both dictionary output and string JSON
versions.

```python
>>> person = Person.objects.get(id=1)
>>> data = PersonSchema.from_orm(person)
>>> data
PersonSchema(id=1, name='Mr. Smith')
>>> data.dict()
{'id':1, 'name':'Mr. Smith'}
>>> data.json()
'{"id":1, "name":"Mr. Smith"}'
```

Multiple Items: or a queryset (or list)

```python
>>> persons = Person.objects.all()
>>> data = [PersonSchema.from_orm(i).dict() for i in persons]
[{'id':1, 'name':'Mr. Smith'},{'id': 2, 'name': 'Mrs. Smith'}...]
```

## Django HTTP responses

It is also possible to return regular django http responses:

```python
from django.http import HttpResponse
from django.shortcuts import redirect


@api.get("/http")
def result_django(request):
    return HttpResponse('some data')   # !!!!


@api.get("/something")
def some_redirect(request):
    return redirect("/some-path")  # !!!!
```
