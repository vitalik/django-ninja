# Tutorial - Handling Responses

## Define a response Schema

**Django Ninja** allows you to define the schema of your responses both for validation and documentation purposes.

We'll create a third operation that will return information about the current Django user.

```python
from ninja import Schema

class UserSchema(Schema):
    username: str
    is_authenticated: bool
    # Unauthenticated users don't have the following fields, so provide defaults.
    email: str = None
    first_name: str = None
    last_name: str = None

@api.get("/me", response=UserSchema)
def me(request):
    return request.user
```

This will convert the Django `User` object into a dictionary of only the defined fields.

### Multiple response types

Let's return a different response if the current user is not authenticated.

```python hl_lines="2-5 7-8 10 12-13"
class UserSchema(Schema):
    username: str
    email: str
    first_name: str
    last_name: str

class Error(Schema):
    message: str

@api.get("/me", response={200: UserSchema, 403: Error})
def me(request):
    if not request.user.is_authenticated:
        return 403, {"message": "Please sign in first"}
    return request.user 
```

As you see, you can return a 2-part tuple which will be interpreted as the HTTP response code and the data.

!!! success

    That concludes the tutorial! Check out the **Other Tutorials** or the **How-to Guides** for more information.