# Overriding Pydantic Config

There are many customizations available for a **Django Ninja `Schema`**, via the schema's
[Pydantic `model_config`](https://docs.pydantic.dev/latest/api/config/). 

!!! info
    Under the hood **Django Ninja** uses [Pydantic Models](https://pydantic-docs.helpmanual.io/usage/models/)
    with all their power and benefits. The alias `Schema` was chosen to avoid confusion in code
    when using Django models, as Pydantic's model class is called Model by default, and conflicts with
    Django's Model class.

## Example Camel Case mode

One interesting config attribute is [`alias_generator`](https://docs.pydantic.dev/latest/api/config/?query=alias_generator#pydantic.config.ConfigDict.alias_generator).
Using Pydantic's example in **Django Ninja** can look something like:

```python hl_lines="10"
from pydantic import ConfigDict
from ninja import Schema


def to_camel(string: str) -> str:
    words = string.split('_')
    return words[0].lower() + ''.join(word.capitalize() for word in words[1:])

class CamelModelSchema(Schema):
    model_config = ConfigDict(alias_generator=to_camel)
    str_field_name: str
    float_field_name: float
```

Keep in mind that when you want modify output for field names (like camel case) - you need to set as well  `populate_by_name` and `by_alias`

```python hl_lines="6 14"
from pydantic import ConfigDict

class UserSchema(ModelSchema):
    model_config = ConfigDict(
        alias_generator = to_camel
        populate_by_name = True,  # !!!!!! <--------
    )
    class Meta:
        model = User
        fields = ["id", "email", "is_staff"]



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
    "isStaff": true
  },
  {
    "id": 2,
    "email": "sarah@smith.com",
    "isStaff": false
  }
  ...
]

```


