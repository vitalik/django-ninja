# Filtering

If you want to allow the user to filter your querysets by a number of different attributes, it makes sense
to encapsulate your filters into a `FilterSchema` class. `FilterSchema` is a regular `Schema`, so it's using all the
necessary features of Pydantic, but it also adds some bells and whistles that ease the translation of the user-facing filtering
parameters into database queries. 

Start off with defining a subclass of `FilterSchema`:

```python hl_lines="6 7 8"
from ninja import FilterSchema, Field
from typing import Optional


class BookFilterSchema(FilterSchema):
    name: Optional[str] = Field(q='name__icontains')
    author: Optional[str] = Field(q='author__name__icontains')
    created_after: Optional[datetime] = Field(q='created__gte')
```

Pay attention to the field definition. `FilterSchema` requires that you provide a kwarg `q`, which should contain
a keyword argument name which will then under the hood be used to translate the filter values into a [Q](https://docs.djangoproject.com/en/3.1/topics/db/queries/#complex-lookups-with-q-objects) expression used for filtering the queryset.


Next, use this schema in conjunction with `Query` in your API handler:
```python hl_lines="2"
@api.get("/books")
def list_books(request, filters: BookFilterSchema = Query(...)):
    books = Book.objects.all()
    books = filters.filter(books)
    return books
```

Just like described in [defining query params using schema](./query-params.md#using-schema), Django Ninja converts the fields
defined in `BookFilterSchema` into query parameters.

You can use a shorthand one-liner `.filter()` to apply those filters to your queryset:
```python hl_lines="4"
@api.get("/books")
def list_books(request, filters: BookFilterSchema = Query(...)):
    books = Book.objects.all()
    books = filters.filter(books)
    return books
```

Alternatively, you can get the prepared `Q`-expression and perform the filtering yourself.
That can be useful, when you have some additional queryset filtering on top of what you expose to the API:
```python hl_lines="4 5 7 8"
@api.get("/books")
def list_books(request, filters: BookFilterSchema = Query(...)):

    # Never serve books from inactive publishers and authors
    q = Q(author__is_active=True) | Q(publisher__is_active=True)
    
    # But allow filtering the rest of the books
    q &= filters.get_filter_expression()
    return Book.objects.filter(q)
```

By default, the filters will behave the following way:

* `None` values will be ignored and not filtered against;
* Every non-`None` field will be converted into a `Q`-expression based on the `Field` definition of each field;
* All `Q`-expressions will be merged into one using `AND` logical operator;
* The resulting `Q`-expression is used to filter the queryset and return you a qeryset with a `.filter` clause applied.


## Filtering by Nones
You can make the `FilterSchema` treat `None` as a valid value that should be filtered against.

This can be done on a field level with a `ignore_none` kwarg:
```python hl_lines="3"
class BookFilterSchema(FilterSchema):
    name: Optional[str] = Field(q='name__icontains')
    tag: Optional[str] = Field(q='tag', ignore_none=False)
```

This way when no other value for `"tag"` is provided by the user, the filtering will always include a condition `tag=None`.

You can also specify this settings for all fields at the same time in the Config:
```python hl_lines="6"
class BookFilterSchema(FilterSchema):
    name: Optional[str] = Field(q='name__icontains')
    tag: Optional[str] = Field(q='tag', ignore_none=False)
    
    class Config:
        ignore_none = False
```


## Combining expressions
By default filters are joined together using `AND` operator. This can be changed in the schema Config:

```python
class BookFilterSchema(FilterSchema):
    name: Optional[str] = Field(q='name__icontains')
    author: Optional[str] = Field(q='author__name__icontains')
    created_after: Optional[datetime] = Field(q='created__gte')
    
    class Config:
        expression_connector = 'OR'     # can be 'AND', 'OR', 'XOR'
```

With such filtering configuration the endpoint...
```python
http://localhost:8000/api/books?name=harry&author=poe
```
...will return Harry Potter series as well as books from Edgar Allan Poe.


## Custom expressions
Sometimes you might want to have complex filtering scenarios that cannot be handled by individual Field annotations.
For such cases you can implement your own custom logic in a `custom_expression` method:

```python
class BookFilterSchema(FilterSchema):
    name: Optional[str]         # No need to supply "q" kwarg
    popular: Optional[bool]     # when custom expression is used

    def custom_expression(self) -> Q:
        q = Q()
        if self.name:
            q &= Q(name__icontains=self.name)
        if self.popular:
            q &= (
                Q(view_count__gt=1000) |
                Q(downloads__gt=100) |
                Q(tag='popular')
            )
        return q
```