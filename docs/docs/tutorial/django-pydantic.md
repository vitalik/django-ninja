# Schemas from Django models


Schemas are very useful to define your validation rules and responses, but sometimes you need to reflect your database models into schemas and keep changes in sync.

## ModelSchema 

`ModelSchema` is a special base class that can automatically generate schemas from your models.

All you need is to set `model` and `model_fields` attributes on your schema `Config`:


```Python hl_lines="2 5 6 7"
from django.contrib.auth.models import User
from ninja import ModelSchema

class UserSchema(ModelSchema):
    class Config:
        model = User
        model_fields = ['id', 'username', 'first_name', 'last_name']

# Will create schema like this:
# 
# class UserSchema(Schema):
#     id: int
#     username: str
#     first_name: str
#     last_name: str
```

### Excluding model fields

To use all fields **except** few  you can use `model_exclude` configuration:

```Python hl_lines="4"
class UserSchema(ModelSchema):
    class Config:
        model = User
        model_exclude = ['password', 'last_login', 'user_permissions']

# Will create schema like this:
# 
# class UserSchema(Schema):
#     id: int
#     username: str
#     first_name: str
#     last_name: str
#     email: str
#     is_superuser: bool
#     ... and the rest

```

### Overriding fields

To change default annotation for some field or add new one just use annotated attributes as usual. 

```Python hl_lines="1 2 3 4 8"
class GroupSchema(ModelSchema):
    class Config:
        model = Group
        model_fields = ['id', 'name']


class UserSchema(ModelSchema):
    groups: List[GroupSchema] = []

    class Config:
        model = User
        model_fields = ['id', 'username', 'first_name', 'last_name']

```
