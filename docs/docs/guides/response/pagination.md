# Pagination

**Django Ninja** comes with a pagination support. This allows you to split large result sets into individual pages.


To apply pagination to a function - just apply `paginate` decorator:

```python hl_lines="1 4"
from ninja.pagination import paginate

@api.get('/users', response=List[UserSchema])
@paginate
def list_users(request):
    return User.objects.all()
```


That's it!

Now you can query users with `limit` and `offset` GET parameters

```
/api/users?limit=10&offset=0
```

by default limit is set to `100` (you can change it in your settings.py using `NINJA_PAGINATION_PER_PAGE`)


## Built in Pagination Classes

### LimitOffsetPagination (default)

This is the default pagination class (You can change it in your settings.py using `NINJA_PAGINATION_CLASS` path to a class)

```python hl_lines="1 4"
from ninja.pagination import paginate, LimitOffsetPagination

@api.get('/users', response=List[UserSchema])
@paginate(LimitOffsetPagination)
def list_users(request):
    return User.objects.all()
```

Example query:
```
/api/users?limit=10&offset=0
```

this class has two input parameters:

 - `limit` - defines a number of queryset on the page (default = 100, change in NINJA_PAGINATION_PER_PAGE)
 - `offset` - set's the page window offset (default: 0, indexing starts with 0)


### PageNumberPagination
```python hl_lines="1 4"
from ninja.pagination import paginate, PageNumberPagination

@api.get('/users', response=List[UserSchema])
@paginate(PageNumberPagination)
def list_users(request):
    return User.objects.all()
```

Example query:
```
/api/users?page=2
```

this class has one parameter `page` and outputs 100 queryset per page by default  (can be changed with settings.py)

Page numbering start with 1

you can also set custom page_size value individually per view:

```python hl_lines="2"
@api.get("/users")
@paginate(PageNumberPagination, page_size=50)
def list_users(...
```

In addition to the `page` parameter, you can also use the `page_size` parameter to dynamically adjust the number of records displayed per page:

Example query:
```
/api/users?page=2&page_size=20
```

This allows you to temporarily override the page size setting in your request. The request will use the specified `page_size` value if provided. Otherwise, it will use either the value specified in the decorator or the value from `PAGINATION_MAX_PER_PAGE_SIZE` in settings.py if no decorator value is set.

### CursorPagination

Cursor-based pagination provides stable pagination for datasets that may change frequently. Cursor pagination uses base64 encoded tokens to mark positions in the dataset, ensuring consistent results even when items are added or removed.

```python hl_lines="1 4"
from ninja.pagination import paginate, CursorPagination

@api.get('/events', response=List[EventSchema])
@paginate(CursorPagination)
def list_events(request):
    return Event.objects.all()
```

Example query:

```
/api/events?cursor=eyJwIjoiMjAyNC0wMS0wMSIsInIiOmZhbHNlLCJvIjowfQ==
```

this class has two input parameters:

- `cursor` - base64 token representing the current position (optional, starts from beginning if not provided)
- `page_size` - number of items per page (optional)

You can specify the `page_size` value to temporarily override in the request:

```
/api/events?cursor=eyJwIjoiMjAyNC0wMS0wMSIsInIiOmZhbHNlLCJvIjowfQ==&page_size=5
```

This class has a few parameters, which determine how the cursor position is ascertained and the parameter encoded:

- `ordering` - tuple of field names to order the queryset. Use `-` prefix for descending order. The first one of which will be used to encode the position. The ordering field should be unique if possible. A string representation of this field will be used to point to the current position of the cursor. Timestamps work well if each item in the collection is created independently. The paginator can handle some non-uniqueness by adding an offset. Defaults to `("-created",)`, change in `NINJA_PAGINATION_DEFAULT_ORDERING`

- `page_size` - default page size for endpoint. Defaults to `100`, change in `NINJA_PAGINATION_PER_PAGE`
- `max_page_size` - maximum allowed page size for endpoint. Defaults to `100`, change in `NINJA_PAGINATION_MAX_PER_PAGE_SIZE`

Finally, there is a `NINJA_PAGINATION_MAX_OFFSET` setting to limit malicious cursor requests. It defaults to `100`.

The class parameters can be set globally via settings as well as per view:

```python hl_lines="2"
@api.get("/events")
@paginate(CursorPagination, ordering=("start_date", "end_date"), page_size=20, max_page_size=100)
def list_events(request):
    return Event.objects.all()
```

The response includes navigation links and results:

```json
{
  "next": "http://api.example.com/events?cursor=eyJwIjoiMjAyNC0wMS0wMiIsInIiOmZhbHNlLCJvIjowfQ==",
  "previous": "http://api.example.com/events?cursor=eyJwIjoiMjAyNC0wMS0wMSIsInIiOnRydWUsIm8iOjB9",
  "results": [
    { "id": 1, "title": "Event 1", "start_date": "2024-01-01" },
    { "id": 2, "title": "Event 2", "start_date": "2024-01-02" }
  ]
}
```

## Accessing paginator parameters in view function

If you need access to `Input` parameters used for pagination in your view function - use `pass_parameter` argument

In that case input data will be available in `**kwargs`:

```python hl_lines="2 4"
@api.get("/someview")
@paginate(pass_parameter="pagination_info")
def someview(request, **kwargs):
    page = kwargs["pagination_info"].page
    return ...
```


## Creating Custom Pagination Class

To create a custom pagination class you should subclass `ninja.pagination.PaginationBase` and override the `Input` and `Output` schema classes and `paginate_queryset(self, queryset, request, **params)` method:

 - The `Input` schema is a Schema class that describes parameters that should be passed to your paginator (f.e. page-number or limit/offset values).
 - The `Output` schema describes schema for page output (f.e. count/next-page/items/etc).
 - The `paginate_queryset` method is passed the initial queryset and should return an iterable object that contains only the data in the requested page. This method accepts the following arguments:
    - `queryset`: a queryset (or iterable) returned by the api function
    - `pagination` - the paginator.Input parameters (parsed and validated)
    - `**params`: kwargs that will contain all the arguments that decorated function received 


Example:

```python hl_lines="7 11 16 26"
from ninja.pagination import paginate, PaginationBase
from ninja import Schema


class CustomPagination(PaginationBase):
    # only `skip` param, defaults to 5 per page
    class Input(Schema):
        skip: int
        

    class Output(Schema):
        items: List[Any] # `items` is a default attribute
        total: int
        per_page: int

    def paginate_queryset(self, queryset, pagination: Input, **params):
        skip = pagination.skip
        return {
            'items': queryset[skip : skip + 5],
            'total': queryset.count(),
            'per_page': 5,
        }


@api.get('/users', response=List[UserSchema])
@paginate(CustomPagination)
def list_users(request):
    return User.objects.all()
```

Tip: You can access request object from params:

```python
def paginate_queryset(self, queryset, pagination: Input, **params):
    request = params["request"]
```

#### Async Pagination

Standard **Django Ninja** pagination classes support async. If you wish to handle async requests with a custom pagination class, you should subclass `ninja.pagination.AsyncPaginationBase` and override the `apaginate_queryset(self, queryset, request, **params)` method.

### Output attribute

By default page items are placed to `'items'` attribute. To override this behaviour use `items_attribute`:

```python hl_lines="4 8"
class CustomPagination(PaginationBase):
    ...
    class Output(Schema):
        results: List[Any]
        total: int
        per_page: int
    
    items_attribute: str = "results"

```


## Apply pagination to multiple operations at once

There is often a case when you need to add pagination to all views that returns querysets or list

You can use a builtin router class (`RouterPaginated`) that automatically injects pagination to all operations that defined `response=List[SomeSchema]`:

```python hl_lines="1 3 6 10"
from ninja.pagination import RouterPaginated

router = RouterPaginated()


@router.get("/items", response=List[MySchema])
def items(request):
    return MyModel.objects.all()

@router.get("/other-items", response=List[OtherSchema])
def other_items(request):
    return OtherModel.objects.all()

```

In this example both operations will have pagination enabled

to apply pagination to main `api` instance use `default_router` argument:


```python
api = NinjaAPI(default_router=RouterPaginated())

@api.get(...
```
