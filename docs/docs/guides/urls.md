# Reverse Resolution of URLS

A reverse URL name is generated for each method in a Django Ninja Schema (or `Router`).

## How URLs are generated

The URLs are all contained within a namespace, which defaults to `"api-1.0.0"`, and each URL name matches the function it is decorated. 

For example:

```python
api = NinjaAPI()

@api.get("/")
def index(request):
    ...

index_url = reverse_lazy("api-1.0.0:index")
```

This implicit URL name will only be set for the first operation for each API path.  If you *don't* want any implicit reverse URL name generated, just explicitly specify `url_name=""` (an empty string) on the method decorator.

### Changing the URL name

Rather than using the default URL name, you can specify it explicitly as a property on the method decorator.

```python
@api.get("/users", url_name="user_list")
def users(request):
    ...

users_url = reverse_lazy("api-1.0.0:user_list")
```

This will override any implicit URL name to this API path.


#### Overriding default url names

You can also override implicit url naming by overwriting the `get_operation_url_name` method:

```python
class MyAPI(NinjaAPI):
    def get_operation_url_name(self, operation, router):
        return operation.view_func.__name__ + '_my_extra_suffix'

api = MyAPI()
```

### Customizing the namespace

The default URL namespace is built by prepending the Schema's version with `"api-"`, however you can explicitly specify the namespace by overriding the `urls_namespace` attribute of the `NinjaAPI` Schema class.

```python

api = NinjaAPI(auth=token_auth, version='2')
api_private = NinjaAPI(auth=session_auth, urls_namespace='private_api')

api_users_url = reverse_lazy("api-2:users")
private_api_admins_url = reverse_lazy("private_api:admins")
```
