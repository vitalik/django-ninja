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
    name: Optional[str] = None
    author: Optional[str] = None
    created_after: Optional[datetime] = None
```


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

Under the hood, `FilterSchema` converts its fields into [Q expressions](https://docs.djangoproject.com/en/3.1/topics/db/queries/#complex-lookups-with-q-objects) which it then combines and uses to filter your queryset.


Alternatively to using the `.filter` method, you can get the prepared `Q`-expression and perform the filtering yourself.
That can be useful, when you have some additional queryset filtering on top of what you expose to the user through the API:
```python hl_lines="5 8"
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
* The resulting `Q`-expression is used to filter the queryset and return you a queryset with a `.filter` clause applied.

## Customizing Fields
By default, `FilterSet` will use the field names to generate Q expressions:
```python
class BookFilterSchema(FilterSchema):
    name: Optional[str] = None
```
The `name` field will be converted into `Q(name=...)` expression.

When your database lookups are more complicated than that, you can explicitly specify them in the field definition using a `"q"` kwarg:
```python hl_lines="2"
class BookFilterSchema(FilterSchema):
    name: Optional[str] = Field(None, q='name__icontains')
```
You can even specify multiple lookup keyword argument names as a list:
```python hl_lines="2 3 4"
class BookFilterSchema(FilterSchema):
    search: Optional[str] = Field(None, q=['name__icontains',
                                     'author__name__icontains',
                                     'publisher__name__icontains'])
```
And to make generic fields, you can make the field name implicit by skipping it:
```python hl_lines="2"
IContainsField = Annotated[Optional[str], Field(None, q='__icontains')]

class BookFilterSchema(FilterSchema):
    name: IContainsField
```
By default, field-level expressions are combined using `"OR"` connector, so with the above setup, a query parameter `?search=foobar` will search for books that have "foobar" in either of their name, author or publisher.


## Combining expressions
By default,

* Field-level expressions are joined together using `OR` operator.
* The fields themselves are joined together using `AND` operator.

So, with the following `FilterSchema`...
```python
class BookFilterSchema(FilterSchema):
    search: Optional[str] = Field(None, q=['name__icontains', 'author__name__icontains'])
    popular: Optional[bool] = None
```
...and the following query parameters from the user
```
http://localhost:8000/api/books?search=harry&popular=true
```
the `FilterSchema` instance will look for popular books that have `harry` in the book's _or_ author's name. 


You can customize this behavior using an `expression_connector` argument in field-level and class-level definition:
```python hl_lines="3 7"
class BookFilterSchema(FilterSchema):
    active: Optional[bool] = Field(None, q=['is_active', 'publisher__is_active'],
                                   expression_connector='AND')
    name: Optional[str] = Field(None, q='name__icontains')
    
    class Config:
        expression_connector = 'OR'
```

An expression connector can take the values of `"OR"`, `"AND"` and `"XOR"`, but the latter is only [supported](https://docs.djangoproject.com/en/4.1/ref/models/querysets/#xor) in Django starting with 4.1.

Now, a request with these query parameters 
```
http://localhost:8000/api/books?name=harry&active=true
```
...shall search for books that have `harry` in their name _or_ are active themselves _and_ are published by active publishers.


## Filtering by Nones
You can make the `FilterSchema` treat `None` as a valid value that should be filtered against.

This can be done on a field level with a `ignore_none` kwarg:
```python hl_lines="3"
class BookFilterSchema(FilterSchema):
    name: Optional[str] = Field(None, q='name__icontains')
    tag: Optional[str] = Field(None, q='tag', ignore_none=False)
```

This way when no other value for `"tag"` is provided by the user, the filtering will always include a condition `tag=None`.

You can also specify this settings for all fields at the same time in the Config:
```python hl_lines="6"
class BookFilterSchema(FilterSchema):
    name: Optional[str] = Field(None, q='name__icontains')
    tag: Optional[str] = Field(None, q='tag', ignore_none=False)
    
    class Config:
        ignore_none = False
```


## Custom expressions
Sometimes you might want to have complex filtering scenarios that cannot be handled by individual Field annotations.
For such cases you can implement your field filtering logic as a custom method. Simply define a method called `filter_<fieldname>` which takes a filter value and returns a Q expression:

```python hl_lines="5"
class BookFilterSchema(FilterSchema):
    tag: Optional[str] = None
    popular: Optional[bool] = None
    
    def filter_popular(self, value: bool) -> Q:
        return Q(view_count__gt=1000) | Q(download_count__gt=100) if value else Q()
```
Such field methods take precedence over what is specified in the `Field()` definition of the corresponding fields.

If that is not enough, you can implement your own custom filtering logic for the entire `FilterSet` class in a `custom_expression` method:

```python hl_lines="5"
class BookFilterSchema(FilterSchema):
    name: Optional[str] = None
    popular: Optional[bool] = None

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
The `custom_expression` method takes precedence over any other definitions described earlier, including `filter_<fieldname>` methods.
