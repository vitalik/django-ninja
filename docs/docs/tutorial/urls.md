# Reverse Resolution of URLS

A reverse URL name is generated for each method in a Django Ninja Schema (or `Router`).

## How URLs are generated

The URLs are all contained within a namespace, which defaults to `"api-1.0.0"`, and each URL name matches the function it is decorated. 

For example:

```Python
api = NinjaAPI()

@api.get("/")
def index(request):
    ...

index_url = reverse_lazy("api-1.0.0:index")
```

### Changing the URL name

Rather than using the default URL name, you can specify it explicitly as a property on the method decorator.

```Python
@api.get("/users", url_name="user_list")
def users(request):
    ...

users_url = reverse_lazy("api-1.0.0:user_list")
```
### Customizing the namespace

The default URL namespace is built by prepending the Schema's version with `"api-"`, however you can explicitly specify the namespace by overriding the `urls_namespace` attribute of the `NinjaAPI` Schema class.

```Python

api = NinjaAPI(auth=token_auth, version='2')
api_private = NinjaAPI(auth=session_auth, urls_namespace='private_api')

api_users_url = reverse_lazy("api-2:users")
private_api_admins_url = reverse_lazy("private_api:admins")
```
