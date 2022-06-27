# Authentication

## Intro

**Django Ninja** provides several tools to help you deal with authentication and authorization easily, rapidly, in a standard way, and without having to study and learn <a href="https://swagger.io/docs/specification/authentication/" target="_blank">all the security specifications</a>.

The core concept is that when you describe an API operation, you can define an authentication object.

```Python hl_lines="2 7"
{!./src/tutorial/authentication/code001.py!}
```

In this example, the client will only be able to call the `pets` method if it uses Django session authentication (the default is cookie based), otherwise an HTTP-401 error will be returned.

## Automatic OpenAPI schema

Here's an example where the client, in order to authenticate, needs to pass a header:

`Authorization: Bearer supersecret`

```Python hl_lines="4 5 6 7 10"
{!./src/tutorial/authentication/bearer01.py!}
```

Now go to the docs at <a href="http://localhost:8000/api/docs" target="_blank">http://localhost:8000/api/docs</a>.


![Swagger UI Auth](../img/auth-swagger-ui.png)

Now, when you click the **Authorize** button, you will get a prompt to input your authentication token.

![Swagger UI Auth](../img/auth-swagger-ui-prompt.png)

When you do test calls, the Authorization header will be passed for every request.


## Global authentication 

In case you need to secure **all** methods of your API, you can pass the `auth` argument to the `NinjaAPI` constructor:


```Python hl_lines="11 19"
from ninja import NinjaAPI, Form
from ninja.security import HttpBearer


class GlobalAuth(HttpBearer):
    def authenticate(self, request, token):
        if token == "supersecret":
            return token


api = NinjaAPI(auth=GlobalAuth())

# @api.get(...)
# def ...

# @api.post(...)
# def ...
```

And, if you need to overrule some of those methods, you can do that on the operation level again by passing the `auth` argument. In this example, authentication will be disabled for the `/token` operation:

```Python hl_lines="19"
{!./src/tutorial/authentication/global01.py!}
```

## Available auth options

### Custom function


The "`auth=`" argument accepts any Callable object. **NinjaAPI** passes authentication only if the callable object returns a value that can be **converted to boolean True**. This return value will be assigned to the `request.auth` attribute.

```Python hl_lines="1 2 3 6"
{!./src/tutorial/authentication/code002.py!}
```


### API Key

Some API's use API keys for authorization. An API key is a token that a client provides when making API calls to identify itself. The key can be sent in the query string:
```
GET /something?api_key=abcdef12345
```

or as a request header:

```
GET /something HTTP/1.1
X-API-Key: abcdef12345
```

or as a cookie:

```
GET /something HTTP/1.1
Cookie: X-API-KEY=abcdef12345
```

**Django Ninja** comes with built-in classes to help you handle these cases.


#### in Query

```Python hl_lines="1 2 5 6 7 8 9 10 11 12"
{!./src/tutorial/authentication/apikey01.py!}
```

In this example we take a token from `GET['api_key']` and find a `Client` in the database that corresponds to this key. The Client instance will be set to the `request.auth` attribute.

Note: **`param_name`** is the name of the GET parameter that will be checked for. If not set, the default of "`key`" will be used.


#### in Header

```Python hl_lines="1 4"
{!./src/tutorial/authentication/apikey02.py!}
```

#### in Cookie

```Python hl_lines="1 4"
{!./src/tutorial/authentication/apikey03.py!}
```



### HTTP Bearer

```Python hl_lines="1 4 5 6 7"
{!./src/tutorial/authentication/bearer01.py!}
```

### HTTP Basic Auth

```Python hl_lines="1 4 5 6 7"
{!./src/tutorial/authentication/basic01.py!}
```


## Multiple authenticators

The **`auth`** argument also allows you to pass multiple authenticators:

```Python hl_lines="18"
{!./src/tutorial/authentication/multiple01.py!}
```

In this case **Django Ninja** will first check the API key `GET`, and if not set or invalid will check the `header` key.
If both are invalid, it will raise an authentication error to the response.


## Router authentication

Use `auth` argument on Router to apply authenticator to all operations declared in it:

```Python
api.add_router("/events/", events_router, auth=BasicAuth())
```

or using router constructor
```Python
router = Router(auth=BasicAuth())
```


## Custom exceptions

Raising an exception that has an exception handler will return the response from that handler in
the same way an operation would:

```Python hl_lines="1 4"
{!./src/tutorial/authentication/bearer02.py!}
```

See [Handling errors](errors.md) for more information.
