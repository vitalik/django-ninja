# Overriding Pydantic Config

There are many customizations available for a **Django Ninja `Schema`**, via the schema's
[Pydantic `Config` class](https://pydantic-docs.helpmanual.io/usage/model_config/). 

!!! info
    Under the hood **Django Ninja** uses [Pydantic Models](https://pydantic-docs.helpmanual.io/usage/models/)
    with all their power and benefits. The alias `Schema` was chosen to avoid confusion in code
    when using Django models, as Pydantic's model class is called Model by default, and conflicts with
    Django's Model class.

## Automatic Camel Case Aliases

One useful `Config` attribute is [`alias_generator`](https://pydantic-docs.helpmanual.io/usage/model_config/#alias-generator).
We can use it to automatically generate aliases for field names with a given function. This is mostly commonly used to create
an API that uses camelCase for its property names.
Using Pydantic's example in **Django Ninja** can look something like:

```python hl_lines="9 10"
from ninja import Schema
from pydantic.alias_generators import to_camel


class CamelModelSchema(Schema):
    str_field_name: str
    float_field_name: float

    class Config(Schema.Config):
        alias_generator = to_camel
```

!!! note
    When overriding the schema's `Config`, it is necessary to inherit from the base `Config` class. 

To alias `ModelSchema`'s field names, you'll also need to set `populate_by_name` on the `Schema` config and 
enable `by_alias` in all endpoints using the model.

```python hl_lines="4 11"
class UserSchema(ModelSchema):
    class Config(Schema.Config):
        alias_generator = to_camel
        populate_by_name = True  # !!!!!! <--------
        
    class Meta:
        model = User
        model_fields = ["id", "email", "created_date"]


@api.get("/users", response=list[UserSchema], by_alias=True) # !!!!!! <-------- by_alias
def get_users(request):
    return User.objects.all()

```

results:

```JSON
[
  {
    "id": 1,
    "email": "tim@apple.com",
    "createdDate": "2011-08-24"
  },
  {
    "id": 2,
    "email": "sarah@smith.com",
    "createdDate": "2012-03-06"
  },
  ...
]

```

## Custom Config from Django Model

When using [`create_schema`](django-pydantic-create-schema.md#create_schema), the resulting
schema can be used to build another class with a custom config like:

```python hl_lines="10"
from django.contrib.auth.models import User
from ninja.orm import create_schema


BaseUserSchema = create_schema(User)


class UserSchema(BaseUserSchema):

    class Config(BaseUserSchema.Config):
        ...
```
