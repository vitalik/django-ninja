# Authorization

## Intro
**Django Ninja** provides a convenient way to handle permission based authorization. You can use it together with the authentication tools or alone. 

With Django Ninja's provied tools for authentication and authorization you can easily implement a complete security-flow based on Django's user and permission - also with groups - system.

## Permission Classes
You can easily create permission classes, that will handle your security-flow:
```python
from ninja.security import BasePermission

class CustomPermission(BasePermission):
    def has_permission(self, request, permission):
        # return falsy type for authorization failure
```
Now you can add your permission class to an api instance, a router or an endpoint:
```python
# ...
@api.get("/awesome-endpoint", perm=CustomPermission("awesome-endpoint.access"))
def awesome_endpoint(request):
    # ...
```

# Working together with Authentication
All authorization processes are started afther authentication to achieve an easy way for combining them.

## Example
When you're using an authentication workflow that assignes the `request.auth` attribute to a django user object, you can implement your permission based authorization in this way: 
```python
class DjangoPermission(BasePermission):
    def has_permission(self, request, permission):
        user = request.auth
        if user:
            return user.has_perm(permission)
```
Your endpoint could look like this:
```python
@api.get("/secure-endpoint", auth=YourAuth(), perm=DjangoPermission("trust.me"))
def secure_endpoint(request):
    # ...
```
Remember that in this case, `YourAuth` must set `request.auth` to a django user.
