# Schemas from Django models


Schemas are very useful to define your validation rules and responses, but sometimes you need to reflect your database models into schemas and keep changes in sync.

## ModelSchema 

`ModelSchema` is a special base class that can automatically generate schemas from your models. Under the hood it converts your models Django fields into
pydantic type annotations. `ModelSchema` inherits from `Schema`, and is just a `Schema` with a Django field -> pydantic field conversion step. All other `Schema`
related configuration and inheritance is the same.

### Configuration

To configure a `ModelSchema` you define a `Meta` class attribute just like in Django. This `Meta` class will be validated by `ninja.orm.metaclass.MetaConf`.

```Python
class MetaConf:  # summary
    model: Django model being used to create the Schema
    fields: List of field names in the model to use. Defaults to '__all__' which includes all fields
    exclude: List of field names to exclude
    optional_fields: List of field names which will be optional, can also take '__all__'
    depth: If > 0 schema will also be created for the nested ForeignKeys and Many2Many (with the provided depth of lookup)
    primary_key_optional: Defaults to True, controls if django's primary_key=True field in the provided model is required
```

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

### Non-Django Model Configuration

The `Meta` class is only used for configuring the interaction between the django model and the underlying
`Schema`. To configure the pydantic model underlying the `Schema` define, `model_config` in your
`ModelSchema` class, or [use the deprecated by pydantic `class Config`](https://docs.pydantic.dev/latest/concepts/config/).

```Python
class UserSlimGetSchema(ModelSchema):
    # pydantic config
    # -- 
    model_config = {"validate_default": True}
    # OR
    class Config:
        validate_default = True
    # --

    class Meta:
        model = User
        fields = ["id", "name"]
```

### Inheritance

Because a `ModelSchema` is just a child of `Schema`, which is in turn just a child of pydantic `BaseModel`, you
can do some convenient inheritance to handle more advanced configuration scenarios.

!!! Warning
    Beware that pydantic v2 does not always respect MRO: https://github.com/pydantic/pydantic/issues/9992

```python
    from ninja import Schema, ModelSchema
    from pydantic import model_serializer
    from django.db import models

    # <proj_schemas.py>
    def _my_magic_serializer(self, handler):
        dump = handler(self)
        dump["magic"] = "shazam"
        return dump


    class ProjSchema(Schema):
        # pydantic configuration
        _my_magic_serilizer = model_serializer(mode="wrap")(_my_magic_serializer)
        model_config = {"arbitrary_types_allowed": True}


    class ProjModelSchema(ProjSchema, ModelSchema):
        # ModelSchema specific configuration
        pass


    class ProjMeta:
        # ModelSchema Meta defaults
        primary_key_optional = False

    # </proj_schemas.py>


    # <models.py>
    class Item(models.Model):
        name = models.CharField(max_length=64)
        type = models.CharField(max_length=64)
        desc = models.CharField(max_length=255, blank=True, null=True)

        class Meta:
            app_label = "test"


    class Event(models.Model):
        name = models.CharField(max_length=64)
        action = models.CharField(max_length=64)

        class Meta:
            app_label = "test"

    # </models.py>


    # <schemas.py>
    # All schemas will be using the configuration defined in parent Schemas
    class ItemSlimGetSchema(ProjModelSchema):
        class Meta(ProjMeta):
            model = Item
            fields = ["id", "name"]


    class ItemGetSchema(ItemSlimGetSchema):
        class Meta(ItemSlimGetSchema.Meta):
            # inherits model, and the parents fields are already set in __annotations__
            fields = ["type", "desc"]


    class EventGetSchema(ProjModelSchema):
        class Meta(ProjMeta):
            model = Event
            fields = ["id", "name"]


    class ItemSummarySchema(ProjSchema):
        model_config = {
            "title": "Item Summary"
        }
        name: str
        event: EventGetSchema
        item: ItemGetSchema

    # </schemas.py>
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

To change default annotation for some field, or to add a new field, just use annotated attributes as usual since a `ModelSchema` is
in the end just a `Schema`.

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


### Inheritance

ModelSchemas can utilize inheritance. The `Meta` class is not inherited implicitly and must have an explicit parent if desired.

```Python
class ProjectBaseSchema(Schema):
    # global pydantic config, hooks, etc
    model_config = {}

class ProjectBaseModelSchema(ModelSchema, ProjectBaseSchema):

    class Meta:
        primary_key_optional = False

class UserSlimGetSchema(ProjectBaseModelSchema):
    class Meta(ProjectBaseModelSchema.Meta):
        model = User
        fields = ["id", "username"]

class UserFullGetSchema(UserSlimGetSchema):
    class Meta(UserSlimGetSchema.Meta):
        model = Item
        fields = ["id", "slug"]
```