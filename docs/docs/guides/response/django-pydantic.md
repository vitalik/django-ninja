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


### Custom fields types

For each Django field it encounters, `ModelSchema` uses the default `Field.get_internal_type` method
to find the correct representation in Pydantic schema (python type). This process works fine for the built-in field
types, but there are cases where the user wants to create or use a custom field, with its own mapping to
python type. In this case you should use `register_field` method to tell django-ninja which type should this django field represent:

```python hl_lines="4 7 8 9"
# models.py

class MyModel(models.Modle):
    embedding = pgvector.VectorField()

# schemas.py
from ninja.orm import register_field

register_field('VectorField', list[float])

```

#### PatchDict

Another way to work with patch request data is a `PatchDict` container which allows you to make 
a schema with all optional fields and get a dict with **only** fields that was provide

```Python hl_lines="1 11"
from ninja import PatchDict

class GroupSchema(Schema):
    # You do not have to make fields optional it will be converted by PatchDict
    name: str
    description: str
    due_date: date


@api.patch("/patch/{pk}")
def modify_data(request, pk: int, payload: PatchDict[GroupSchema]):
    obj = MyModel.objects.get(pk=pk)

    for attr, value in payload.items():
        setattr(obj, attr, value)
    
    obj.save()

```

in this example the `payload` argument will be a type of `dict` only fields that were passed in request and validated using `GroupSchema`
