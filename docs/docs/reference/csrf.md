# CSRF

## What is the CSRF protection and why is it needed?
Cross-site request forgery is a type of vulnerabilities where a user's web browser connects to a malicious page, which triggers request to your backend (using hidden forms, JavaScript `fetch` or `XMLHttpRequest`, or other methods), that could interpret those as legitimate as some credentials saved on the user's web browser (like cookies) may be automatically embedded.

Your backend must be able to differentiate between legitimate and malicious requests. This can be done in several ways.

If you are not familiar with CSRF attacks it is recommended to at leat read:
- the [Wikipedia article about CSRF](https://en.wikipedia.org/wiki/Cross-site_request_forgery)
For a more complete understanding of different mitigations and their implications, you may also read:
- the [Owasp Community Page about CSRF](https://owasp.org/www-community/attacks/csrf)
- the [OWASP Cheat Sheet about Cross-Site Request Forgery Prevention](https://cheatsheetseries.owasp.org/cheatsheets/Cross-Site_Request_Forgery_Prevention_Cheat_Sheet.html)


## How to protect with Django Ninja
### Use an authentication method that doesn't get automatically transmitted by request from another site
CSRF can happen because the cookies are automatically included in requests started from another site.
Not using cookies but another method to transfer and consume the token, like the `Authorization: Bearer` header for exemple, mitigates this attack.

### Django CSRF protection
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


You can use the Django [ensure_csrf_cookie](https://docs.djangoproject.com/en/4.2/ref/csrf/#django.views.decorators.csrf.ensure_csrf_cookie) decorator on an unprotected route to make it include a `Set-Cookie` header for the CSRF token (note that the route decorator must come upper than the [ensure_csrf_cookie](https://docs.djangoproject.com/en/4.2/ref/csrf/#django.views.decorators.csrf.ensure_csrf_cookie) decorator).


You may use the [Using CSRF protection with AJAX](https://docs.djangoproject.com/en/4.2/howto/csrf/#using-csrf-protection-with-ajax) and [Setting the token on the AJAX request](https://docs.djangoproject.com/en/4.2/howto/csrf/#setting-the-token-on-the-ajax-request) part of the [How to use Django’s CSRF protection](https://docs.djangoproject.com/en/4.2/howto/csrf/) to know how to handle that CSRF protection token in your frontend code.

## A word about CORS
You may want to set-up your frontend and API on different sites (in that case, you may check [django-cors-headers](https://github.com/adamchainz/django-cors-headers)).
While not directly related to CSRF, CORS (Cross-Origin Resource Sharing) may cause problems in case you are defining the CSRF cookie on another site than the frontend consuming it.
You may check the [django-cors-headers README](https://github.com/adamchainz/django-cors-headers#readme) then.
