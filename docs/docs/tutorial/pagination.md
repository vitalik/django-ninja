# Pagination (beta)

Django Ninja comes with a pagination. This allows you to split large result sets into individual pages.


To apply pagination to a function - just apply `paginate` decorator:

```Python hl_lines="1 4"
from ninja.pagination import paginate

@api.get('/users', response=List[UserSchema])
@paginate
def list_users(request, **kwargs):
    return User.objects.all()
```

!!! note
    Once you applied pagination - you need also add `**kwargs` parameters to your function (it will store pagination filters)

That's it!

Now you can query users with `limit` and `offset` GET parameters

```
/api/users?limit=10&offset=0
```

by default limit is set to `100` (you can change it in your settings.py using `NINJA_PAGINATION_PER_PAGE`)


## Built in Pagination Classes

### LimitOffsetPagination (default)

This is the default pagination class (You can change it in your settings.py using `NINJA_PAGINATION_CLASS` path to a class)

```Python hl_lines="1 4"
from ninja.pagination import paginate, LimitOffsetPagination

@api.get('/users', response=List[UserSchema])
@paginate(LimitOffsetPagination)
def list_users(request, **kwargs):
    return User.objects.all()
```

Example query:
```
/api/users?limit=10&offset=0
```

this class has two input parameters:

 - `limit` - defines a number of items on the page (default = 100, change in NINJA_PAGINATION_PER_PAGE)
 - `offset` - set's the page window offset (default: 0, indexing starts with 0)


### PageNumberPagination
```Python hl_lines="1 4"
from ninja.pagination import paginate, PageNumberPagination

@api.get('/users', response=List[UserSchema])
@paginate(PageNumberPagination)
def list_users(request, **kwargs):
    return User.objects.all()
```

Example query:
```
/api/users?page=2
```

this class has one parameter `page` and outputs 100 items per page by default  (can be changed with settings.py)

Page numbering start with 1

you can also set custom per_page value individually per view:

```Python hl_lines="2"
@api.get("/users")
@paginate(PageNumberPagination, per_page=50)
def list_users(...
```




## Creating Custom Pagination Class

To create a custom pagination class you should subclass `ninja.pagination.PaginationBase` and override the `Input` schema class and `paginate_queryset(self, items, request, **params)` method:

 - The `Input` schema is a Schema class that describes parameters that should be passed to your paginator (f.e. page-number or limit/offset values).
 - The `paginate_queryset` method is passed the initial queryset and should return an iterable object that contains only the data in the requested page. This method accepts the following arguments:
    - `items`: a queryset (or iterable) returned by the api function
    - `request`: django http request object
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
