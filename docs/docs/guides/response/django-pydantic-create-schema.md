# Using create_schema

Under the hood, [`ModelSchema`](django-pydantic.md#modelschema) uses the `create_schema` function.
This is a more advanced (and less safe) method - please use it carefully.

## `create_schema`

**Django Ninja** comes with a helper function `create_schema`:

```python
def create_schema(
    model, # django model
    name = "", # name for the generated class, if empty model names is used
    depth = 0, # if > 0 schema will also be created for the nested ForeignKeys and Many2Many (with the provided depth of lookup)
    fields: list[str] = None, # if passed - ONLY these fields will added to schema
    exclude: list[str] = None, # if passed - these fields will be excluded from schema
    optional_fields: list[str] | str = None, # if passed - these fields will not be required on schema (use '__all__' to mark ALL fields required)
    custom_fields: list[tuple(str, Any, Any)] = None, # if passed - this will override default field types (or add new fields)
)
```


Take this example:

```python hl_lines="2 4"
from django.contrib.auth.models import User
from ninja.orm import create_schema

UserSchema = create_schema(User)

# Will create schema like this:
# 
# class UserSchema(Schema):
#     id: int
#     username: str
#     first_name: str
#     last_name: str
#     password: str
#     last_login: datetime
#     is_superuser: bool
#     email: str
#     ... and the rest

```

!!! Warning
    By default `create_schema` builds a schema with ALL model fields.
    This can lead to accidental unwanted data exposure (like hashed password, in the above example).
    <br>
    **Always** use `fields` or `exclude` arguments to explicitly define list of attributes.

### Using `fields`

```python hl_lines="1"
UserSchema = create_schema(User, fields=['id', 'username'])

# Will create schema like this:
# 
# class UserSchema(Schema):
#     id: int
#     username: str

```

### Using `exclude`

```python hl_lines="1 2"
UserSchema = create_schema(User, exclude=[
    'password', 'last_login', 'is_superuser', 'is_staff', 'groups', 'user_permissions']
)

# Will create schema without excluded fields:
# 
# class UserSchema(Schema):
#    id: int
#    username: str
#    first_name: str
#    last_name: str
#    email: str
#    is_active: bool
#    date_joined: datetime
```

### Using `depth`

The `depth` argument allows you to introspect the Django model into the Related fields(ForeignKey, OneToOne, ManyToMany).

```python hl_lines="1 7"
UserSchema = create_schema(User, depth=1, fields=['username', 'groups'])

# Will create the following schema:
#
# class UserSchema(Schema):
#    username: str
#    groups: List[Group]
```

Note here that groups became a `List[Group]` - many2many field introspected 1 level deeper and created schema as well for group:

```python
class Group(Schema):
    id: int
    name: str
    permissions: List[int]
```
