# Altering the Response

Sometimes you'll want to change the response just before it gets served, for example, to add a header or alter a cookie.

To do this, simply declare a function parameter with a type of `HttpResponse`:

```python
from django.http import HttpRequest, HttpResponse

@api.get("/cookie/")
def feed_cookiemonster(request: HttpRequest, response: HttpResponse):
    # Set a cookie.
    response.set_cookie("cookie", "delicious")
    # Set a header.
    response["X-Cookiemonster"] = "blue"
    return {"cookiemonster_happy": True}
```


## Temporal response object

This response object is used for the base of all responses built by Django Ninja, including error responses. This object is *not* used if a Django `HttpResponse` object is returned directly by an operation.

Obviously this response object won't contain the content yet, but it does have the `content_type` set (but you probably don't want to be changing it).

The `status_code` will get overridden depending on the return value (200 by default, or the status code if a two-part tuple is returned).


## Changing the base response object

You can alter this temporal response object by overriding the `NinjaAPI.create_temporal_response` method.

```python
    def create_temporal_response(self, request: HttpRequest) -> HttpResponse:
        response = super().create_temporal_response(request)
        # Do your magic here...
        return response
```