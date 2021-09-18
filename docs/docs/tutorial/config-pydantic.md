# Overriding Pydantic Config

There are many customizations available for a **Django Ninja `Schema`**, via the schema's
[Pydantic `Config` class](https://pydantic-docs.helpmanual.io/usage/model_config/). 

!!! info
    Under the hood **Django Ninja** uses [Pydantic Models](https://pydantic-docs.helpmanual.io/usage/models/)
    with all their power and benefits. The alias `Schema` was chosen to avoid confusion in code
    when using Django models, as Pydantic's model class is called Model by default, and conflicts with
    Django's Model class.

## Example Camel Case mode

One interesting `Config` attribute is [`alias_generator`](https://pydantic-docs.helpmanual.io/usage/model_config/#alias-generator).
Using Pydantic's example in **Django Ninja** can look something like:

```python hl_lines="12 13"
from ninja import Schema


def to_camel(string: str) -> str:
    return ''.join(word.capitalize() for word in string.split('_'))


class CamelModelSchema(Schema):
    str_field_name: str
    float_field_name: float

    class Config(Schema.Config):
        alias_generator = to_camel
```

!!! note
    When overriding the schema's `Config`, it is necessary to inherit from the base `Config` class. 

## Custom Config from Django Model

When using [`create_schema`](../django-pydantic-create-schema/#create_schema), the resulting
schema can be used to build another class with a custom config like:

```Python hl_lines="10"
from django.contrib.auth.models import User
from ninja.orm import create_schema


BaseUserSchema = create_schema(User)


class UserSchema(BaseUserSchema):

    class Config(BaseUserSchema.Config):
        ...
```
