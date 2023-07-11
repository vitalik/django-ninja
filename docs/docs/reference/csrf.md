# CSRF

By default, **Django Ninja** has CSRF turned **OFF** for all operations.
To turn it on you need to use the `csrf` argument of the NinjaAPI class:




```Python hl_lines="3"
from ninja import NinjaAPI

api = NinjaAPI(csrf=True)
```

<span style="color: red;">Warning</span>: It is not secure to use API's with cookie-based authentication! (like `CookieKey`, or `django_auth`) when csrf is turned OFF.


**Django Ninja** will automatically enable csrf for Cookie based authentication


```Python hl_lines="8"
from ninja import NinjaAPI
from ninja.security import APIKeyCookie

class CookieAuth(APIKeyCookie):
    def authenticate(self, request, key):
        return key == "test"

api = NinjaAPI(auth=CookieAuth())

```


or django-auth based (which is inherited from cookie based auth):

```Python hl_lines="4"
from ninja import NinjaAPI
from ninja.security import django_auth

api = NinjaAPI(auth=django_auth)

```