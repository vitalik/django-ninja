# CSRF

## What is CSRF?
> [Cross Site Request Forgery](https://en.wikipedia.org/wiki/Cross-site_request_forgery) occurs when a malicious website contains a link, a form button or some JavaScript that is intended to perform some action on your website, using the credentials (or location on the network, not covered by this documentation) of a logged-in user who visits the malicious site in their browser.


## How to protect against CSRF with Django Ninja
### Use an authentication method not automatically embedded in the request
CSRF attacks rely on authentication methods that are automatically included in requests started from another site, like [cookies](https://en.wikipedia.org/wiki/HTTP_cookie) or [Basic access authentication](https://en.wikipedia.org/wiki/Basic_access_authentication).
Using an authentication method that does not automatically gets embedded, such as the `Authorization: Bearer` header for exemple, mitigates this attack.


### Use Django's built-in CSRF protection
In case you are using the default Django authentication, which uses cookies, you must also use the default [Django CSRF protection](https://docs.djangoproject.com/en/4.2/ref/csrf/).


By default, **Django Ninja** has CSRF protection turned **OFF** for all operations.
To turn it on you need to use the `csrf` argument of the NinjaAPI class:

```python hl_lines="3"
from ninja import NinjaAPI

api = NinjaAPI(csrf=True)
```

<span style="color: red;">Warning</span>: It is not secure to use API's with cookie-based authentication! (like `CookieKey`, or `django_auth`) when csrf is turned OFF.


**Django Ninja** will automatically enable csrf for Cookie based authentication


```python hl_lines="8"
from ninja import NinjaAPI
from ninja.security import APIKeyCookie

class CookieAuth(APIKeyCookie):
    def authenticate(self, request, key):
        return key == "test"

api = NinjaAPI(auth=CookieAuth())

```


or django-auth based (which is inherited from cookie based auth):

```python hl_lines="4"
from ninja import NinjaAPI
from ninja.security import django_auth

api = NinjaAPI(auth=django_auth)
```


#### Django `ensure_csrf_cookie` decorator
You can use the Django [ensure_csrf_cookie](https://docs.djangoproject.com/en/4.2/ref/csrf/#django.views.decorators.csrf.ensure_csrf_cookie) decorator on an unprotected route to make it include a `Set-Cookie` header for the CSRF token. Note that:

- The route decorator must be executed before (i.e. above) the [ensure_csrf_cookie](https://docs.djangoproject.com/en/4.2/ref/csrf/#django.views.decorators.csrf.ensure_csrf_cookie) decorator).
- You must `csrf_exempt` that route.
- The `ensure_csrf_cookie` decorator works only on a Django `HttpResponse` (and subclasses like `JsonResponse`) and not on a dict like most Django Ninja decorators.
- If you [set a Cookie based authentication (which includes `django_auth`) globally to your API](../guides/authentication.md), you'll have to specifically disable auth on that route (with `auth=None` in the route decorator) as Cookie based authentication would raise an Exception when applied to an unprotected route (for security reasons).

```python hl_lines="4"
from django.http import HttpResponse
from django.views.decorators.csrf import csrf_exempt, ensure_csrf_cookie

@api.post("/csrf")
@ensure_csrf_cookie
@csrf_exempt
def get_csrf_token(request):
    return HttpResponse()
```
A request to that route triggers a response with the adequate `Set-Cookie` header from Django.


#### Frontend code
You may use the [Using CSRF protection with AJAX](https://docs.djangoproject.com/en/4.2/howto/csrf/#using-csrf-protection-with-ajax) and [Setting the token on the AJAX request](https://docs.djangoproject.com/en/4.2/howto/csrf/#setting-the-token-on-the-ajax-request) part of the [How to use Django’s CSRF protection](https://docs.djangoproject.com/en/4.2/howto/csrf/) to know how to handle that CSRF protection token in your frontend code.


## A word about CORS
You may want to set-up your frontend and API on different sites (in that case, you may check [django-cors-headers](https://github.com/adamchainz/django-cors-headers)).
While not directly related to CSRF, CORS (Cross-Origin Resource Sharing) may help in case you are defining the CSRF cookie on another site than the frontend consuming it, as this is not allowed by default by the [Same-origin policy](https://developer.mozilla.org/en-US/docs/Web/Security/Same-origin_policy).
You may check the [django-cors-headers README](https://github.com/adamchainz/django-cors-headers#readme) then.
