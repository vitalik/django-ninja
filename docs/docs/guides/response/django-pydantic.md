# Schemas from Django models


Schemas are very useful to define your validation rules and responses, but sometimes you need to reflect your database models into schemas and keep changes in sync.

## ModelSchema 

`ModelSchema` is a special base class that can automatically generate schemas from your models.

All you need is to set `model` and `fields` attributes on your schema `Meta`:


```python hl_lines="2 5 6 7"
from django.contrib.auth.models import User
from ninja import ModelSchema

class UserSchema(ModelSchema):
    class Meta:
        model = User
        fields = ['id', 'username', 'first_name', 'last_name']

# Will create schema like this:
# 
# class UserSchema(Schema):
#     id: int
#     username: str
#     first_name: str
#     last_name: str
```

### Using ALL model fields

To use all fields from a model - you can pass `__all__` to `fields`:

```python hl_lines="4"
class UserSchema(ModelSchema):
    class Meta:
        model = User
        fields = "__all__"
```
!!! Warning
    Using __all__ is not recommended.
    <br>
    This can lead to accidental unwanted data exposure (like hashed password, in the above example).
    <br>
    General advice - use `fields` to explicitly define list of fields that you want to be visible in API.

### Excluding model fields

To use all fields **except** a few, you can use `exclude` configuration:

```python hl_lines="4"
class UserSchema(ModelSchema):
    class Meta:
        model = User
        exclude = ['password', 'last_login', 'user_permissions']

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

To change default annotation for some field, or to add a new field, just use annotated attributes as usual. 

```python hl_lines="1 2 3 4 8"
class GroupSchema(ModelSchema):
    class Meta:
        model = Group
        fields = ['id', 'name']


class UserSchema(ModelSchema):
    groups: List[GroupSchema] = []

    class Meta:
        model = User
        fields = ['id', 'username', 'first_name', 'last_name']

```


### Making fields optional

Pretty often for PATCH API operations you need to make all fields of your schema optional. To do that, you can use config fields_optional

```python hl_lines="5"
class PatchGroupSchema(ModelSchema):
    class Meta:
        model = Group
        fields = ['id', 'name', 'description'] # Note: all these fields are required on model level
        fields_optional = '__all__'
```

Also, you can define a subset of optional fields instead of `__all__`:

```python
     fields_optional = ['description']
```

When you process input data, you need to tell Pydantic to avoid setting undefined fields to `None`:

```python
@api.patch("/patch/{pk}")
def patch(request, pk: int, payload: PatchGroupSchema):

    # Notice that we set exclude_unset=True
    updated_fields = payload.dict(exclude_unset=True)

    obj = MyModel.objects.get(pk=pk)

    for attr, value in updated_fields.items():
        setattr(obj, attr, value)

    obj.save()


```
