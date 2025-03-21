# Form data

**Django Ninja** also allows you to parse and validate `request.POST` data
(aka `application/x-www-form-urlencoded` or `multipart/form-data`).

## Form Data as params 

```python hl_lines="1 4"
from ninja import NinjaAPI, Form

@api.post("/login")
def login(request, username: Form[str], password: Form[str]):
    return {'username': username, 'password': '*****'}
```

Note the following:

1) You need to import the `Form` class from `ninja`
```python
from ninja import Form
```

2) Use `Form` as default value for your parameter:
```python
username: Form[str]
```

## Using a Schema

In a similar manner to [Body](body.md#declare-it-as-a-parameter), you can use
a Schema to organize your parameters.

```python hl_lines="12"
{!./src/tutorial/form/code01.py!}
```

## Request form + path + query parameters

In a similar manner to [Body](body.md#request-body-path-query-parameters), you can use
Form data in combination with other parameter sources.

You can declare query **and** path **and** form field, **and** etc... parameters at the same time.

**Django Ninja** will recognize that the function parameters that match path
parameters should be **taken from the path**, and that function parameters that
are declared with `Form(...)` should be **taken from the request form fields**, etc.

```python hl_lines="12"
{!./src/tutorial/form/code02.py!}
```
## Mapping Empty Form Field to Default

Form fields that are optional, are often sent with an empty value. This value is
interpreted as an empty string, and thus may fail validation for fields such as `int` or `bool`.

This can be fixed, as described in the Pydantic docs, by using
[Generic Classes as Types](https://pydantic-docs.helpmanual.io/usage/types/#generic-classes-as-types).

```python hl_lines="15 16 23-25"
{!./src/tutorial/form/code03.py!}
```
