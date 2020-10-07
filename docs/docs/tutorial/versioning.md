# Versioning

## Different version numbers

With Django Ninja it's easy to run multiple API version from a single django project.

All you have to do is to create two or more NinjaAPI instance with different `version` argument:


file  **api_v1.py**:

```Python hl_lines="4"
from ninja import NinjaAPI


api = NinjaAPI(version='1.0.0')

@api.get('/hello')
def hello(request):
    return {'message': 'Hello from V1'}

```


file  api_**v2**.py:
```Python hl_lines="4"
from ninja import NinjaAPI


api = NinjaAPI(version='2.0.0')

@api.get('/hello')
def hello(request):
    return {'message': 'Hello from V2'}
```

and then in **urs.py**:

```Python hl_lines="8 9"
...
from api_v1 import api as api_v1
from api_v2 import api as api_v2


urlpatterns = [
    ...
    path('api/v1/', api_v1.urls),
    path('api/v2/', api_v2.urls),
]

```

Now you can go to different docs pages for each version:

 - http://127.0.0.1/api/**v1**/docs
 - http://127.0.0.1/api/**v2**/docs



## Different business logic

Same way you can define different API for different components or areas:

```Python hl_lines="4 7"
...


api = NinjaAPI(auth=token_auth, urls_namespace='public_api')
...

api_private = NinjaAPI(auth=session_auth, urls_namespace='private_api')
...


urlpatterns = [
    ...
    path('api/', api.urls),
    path('internal-api/', api_private.urls),
]

```
!!! note
    if you use different **NinjaAPI** instances - you need to define different `version`s or different `urls_namespace`s
