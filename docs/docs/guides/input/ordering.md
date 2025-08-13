# Ordering

If you want to allow the user to order your querysets by a number of different attributes, you can use the provided class `OrderingSchema`. `OrderingSchema`, as a regular `Schema`, it uses all the
necessary features from Pydantic, and adds some some bells and whistles that will help use transform it into the usual Django queryset ordering.

You can start using it, importing the `OrderingSchema` and using it in your API handler in conjunction with `Query`:

```python hl_lines="4"
from ninja import OrderingSchema

@api.get("/books")
def list_books(request, ordering: OrderingSchema = Query(...)):
    books = Book.objects.all()
    books = ordering.sort(books)
    return books
```

Just like described in [defining query params using schema](./query-params.md#using-schema), Django Ninja converts the fields defined in `OrderingSchema` into query parameters. In this case, the field is only one: `order_by`. This field will accept multiple string values.

You can use a shorthand one-liner `.sort()` to apply the ordering to your queryset:

```python hl_lines="4"
@api.get("/books")
def list_books(request, ordering: OrderingSchema = Query(...)):
    books = Book.objects.all()
    books = ordering.sort(books)
    return books
```

Under the hood, `OrderingSchema` expose a query parameter `order_by` that can be used to order the queryset. The `order_by` parameter expects a list of string, representing the list of field names that will be passed to the `queryset.order_by(*args)` call. This values can be optionally prefixed by a minus sign (`-`) to indicate descending order, following the same standard from Django ORM.

## Restricting Fields

By default, `OrderingSchema` will allow to pass any field name to order the queryset. If you want to restrict the fields that can be used to order the queryset, you can use the `allowed_fields` field in the `OrderingSchema.Meta` class definition:

```python hl_lines="3"
class BookOrderingSchema(OrderingSchema):
    class Meta:
        allowed_fields = ['name', 'created_at']  # Leaving out `author` field
```

This class definition will restrict the fields that can be used to order the queryset to only `name` and `created_at` fields. If the user tries to pass any other field, a `ValidationError` will be raised.

## Default Ordering

If you want to provide a default ordering to your queryset, you can assign a default value in the `order_by` field in the `OrderingSchema` class definition:

```python hl_lines="2"
class BookOrderingSchema(OrderingSchema):
    order_by: List[str] = ['name']
```
