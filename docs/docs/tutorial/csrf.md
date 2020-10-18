# CSRF

By default Django Ninja have CSRF turned **OFF** for all operations. To turn it on you need to use `csrf` argument for NinjaAPI class:




```Python hl_lines="3"
from ninja import NinjaAPI

api = NinjaAPI(csrf=True)
```

<span style="color: red;">Warning</span>: it is not secure to use APIs with cookie based authentication (like `CookieKey`, or `django_auth`)


Django Ninja will prevent you from doing this. So if you would use this:


```Python hl_lines="4"
from ninja import NinjaAPI
from ninja.security import django_auth

api = NinjaAPI(auth=django_auth)

```

This will raise an error. Instead you need to set `csrf` argument to `True` to enable CSRF checks:


```Python hl_lines="4"
from ninja import NinjaAPI
from ninja.security import django_auth

api = NinjaAPI(auth=django_auth, csrf=True)

```
