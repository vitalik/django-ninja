# Pagination

Django Ninja comes with a pagination. This allows you to split large result sets into individual pages.


To apply pagination to a function - just apply `paginate` decorator:

```Python hl_lines="1 4"
from ninja.pagination import paginate

@api.get('/users', response=List[UserSchema])
@paginate
def list_users(request, **kwargs):
    return User.objects.all()
```

Note: once you applied pagination - you need also add `**kwargs` parameters to your function (it will store pagination filters)

That's it!


## Built in Pagination Classes

### LimitOffsetPagination (default)
```Python hl_lines="1 4"
from ninja.pagination import paginate, LimitOffsetPagination

@api.get('/users', response=List[UserSchema])
@paginate(LimitOffsetPagination)
def list_users(request, **kwargs):
    return User.objects.all()
```

### PageNumberPagination
```Python hl_lines="1 4"
from ninja.pagination import paginate, PageNumberPagination

@api.get('/users', response=List[UserSchema])
@paginate(PageNumberPagination)
def list_users(request, **kwargs):
    return User.objects.all()
```



## Creating Custom Pagination Class

To create a custom pagination class you should subclass `ninja.pagination.PaginationBase` and override the `Input` schema class and `paginate_queryset(self, items, request, **params)` method:

 - The `Input` schema is a Schema class that describes parameters that should be passed to your paginator (f.e. page-number or limit/offset values).
 - The `paginate_queryset` method is passed the initial queryset and should return an iterable object that contains only the data in the requested page. This method accepts the following arugments:
    - `items`: a queryset (or iterable) returned by the api function
    - `reques`: django http request object
    - `**params`: kwargs that will contain all the arguments that decorated function recieved (to access pagination input get `params["pagination"]` - it will be a validated instance of your `Input` class) 


Example:

```Python hl_lines="1 5 6 7 8 9 10 11 12 16"
from ninja.pagination import paginate, PaginationBase
from ninja import Schema


class CustomPagination(PaginationBase):
    # only `skip` param, defaults to 5 per page
    class Input(Schema):
        skip: int

    def paginate_queryset(self, items, request, **params):
        skip = params["pagination"].skip
        return items[skip : skip + 5]


@api.get('/users', response=List[UserSchema])
@paginate(CustomPagination)
def list_users(request, **kwargs):
    return User.objects.all()
```