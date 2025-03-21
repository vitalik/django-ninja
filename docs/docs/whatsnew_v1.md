# Welcome to Django Ninja 1.0


To get started install latest version with
```
pip install -U django-ninja
```

django-ninja v1 is compatible with Python 3.7 and above.


Django ninja seres 0.x is still supported but will receive only security updates and critical bug fixes



# What's new in Django Ninja 1.0

## Support for Pydantic2

Pydantic version 2 is re-written in Rust and includes a lot of improvements and features like:

 - Safer types.
 - Better extensibility.
 - Better performance 

By our tests average project can gain some 10% performance increase on average, while some edge parsing/serializing cases can give you 4x boost.

On the other hand it introduces breaking changes and pydantic 1 and 2 are not very compatible - but we tried or best to make this transition easy as possible. So if you used 'Schema' class migration to ninja v1 should be easy. Otherwise follow [pydantic migration guide](https://docs.pydantic.dev/latest/migration/)


Some features that are made possible with pydantic2

### pydantic context

Pydantic now supports context during validation and serialization and Django ninja passes "request" object during request and response work

```Python hl_lines="6 7"
class Payload(Schema):
    id: int
    name: str
    request_path: str

    @staticmethod
    def resolve_request_path(data, context):
        request = context["request"]
        return request.get_full_path()

```

During response a "response_code" is also passed to context

## Schema.Meta

Pydantic now deprecates BaseModel.Config class.  But to keep things consistent with all other django parts we introduce "Meta" class for ModelSchema - which works in a similar way as django's ModelForms:

```Python hl_lines="2 4"
class TxItem(ModelSchema):
    class Meta:
        model = Transaction
        fields = ["id", "account", "amount", "timestamp"]

```

(The "Config" class is still supported, but deprecated)


## Shorter / cleaner parameters syntax

```python
@api.post('/some')
def some_form(request, username: Form[str], password: Form[str]):
    return True
```

instead of

```python
@api.post('/some')
def some_form(request, username: str = Form(...), password: str = Form(...)):
    return True
```

or 

```python
@api.post('/some')
def some_form(request, data: Form[AuthSchema]):
    return True
```


instead of

```python
@api.post('/some')
def some_form(request, data: AuthSchema = Form(...)):
    return True
```



with all the autocompletion in editors


On the other hand the **old syntax is still supported** so you can easily port your project to a newer django-ninja version without much haste 


#### + Annotated

typing.Annotated is also supported:

```Python
@api.get("/annotated")
def annotated(request, data: Annotated[SomeData, Form()]):
    return {"data": data.dict()}

```


## Async auth support

The async authenticators are finally supported. All you have to do is just add `async` to your `authenticate` method:

```Python
class Auth(HttpBearer):
    async def authenticate(self, request, token):
        await asyncio.sleep(1)
        if token == "secret":
            return token

```


## Changed CSRF Behavior


`csrf=True` requirement is no longer required if you use cookie based authentication. Instead CSRF protection is enabled automatically. This also allow you to  mix csrf-protected authenticators and other methods that does not require cookies:

```Python
api = NinjaAPI(auth=[django_auth, Auth()])
```


## Docs

Doc viewer are now configurable and plugable. By default django ninja comes with Swagger and Redoc:

```Python
from ninja import NinjaAPI, Redoc, Swagger


# use redoc
api = NinjaAPI(docs=Redoc()))

# use swagger:
api = NinjaAPI(docs=Swagger())

# set configuration for swagger:
api = NinjaAPI(docs=Swagger({"persistAuthorization": True}))
```

Users now able to create custom docs viewer by inheriting `DocsBase` class

## Router

add_router supports string paths:

```Python
api = NinjaAPI()


api.add_router('/app1', 'myproject.app1.router')
api.add_router('/app2', 'myproject.app2.router')
api.add_router('/app3', 'myproject.app3.router')
api.add_router('/app4', 'myproject.app4.router')
api.add_router('/app5', 'myproject.app5.router')
```


## Decorators

When django ninja decorates a view with .get/.post etc. - it wraps the result of the function (which in most cases are not HttpResponse - but some serializable object) so it's not really possible to use some built-in or 3rd-party decorators like:

```python hl_lines="4"
from django.views.decorators.cache import cache_page

@api.get("/test")
@cache_page(5) # <----- will not work
def test_view(request):
    return {"some": "Complex data"}
```
This example does not work.

Now django ninja introduces a decorator decorate_view that allows inject decorators that work with http response:

```python hl_lines="1 4"
from ninja.decorators import decorate_view

@api.get("/test")
@decorate_view(cache_page(5))
def test_view(request):
    return str(datetime.now())
```


## Paginations

`paginate_queryset` method now takes `request` object


#### Backwards incompatible stuff
 - resolve_xxx(self, ...) - support resolve with (self) is dropped in favor of pydantic build-in functionality
 - pydantic v1 is no longer supported
 - python 3.6 is no longer supported

BTW - if you like this project and still did not give it a github start - please do so ![github star](img/github-star.png)
