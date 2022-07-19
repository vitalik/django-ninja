# Handling errors

**Django Ninja** allows you to install custom exception handlers to deal with how you return responses when errors or handled exceptions occur.

## Custom exception handlers

Let's say you are making API that depends on some external service that is designed to be unavailable at some moments. Instead of throwing default 500 error upon exception - you can handle the error and give some friendly response back to the client (to come back later)

To achieve that you need:

 - 1) create some exception (or use existing one)
 - 2) use api.exception_handler decorator


Example:


```Python hl_lines="9 10"
api = NinjaAPI()

class ServiceUnavailableError(Exception):
    pass


# initializing handler

@api.exception_handler(ServiceUnavailableError)
def service_unavailable(request, exc):
    return api.create_response(
        request,
        {"message": "Please retry later"},
        status=503,
    )


# some logic that throws exception

@api.get("/service")
def some_operation(request):
    if random.choice([True, False]):
        raise ServiceUnavailableError()
    return {"message": "Hello"}

```

Exception handler function takes 2 arguments:

 - **request** - Django http request
 - **exc** - actual exception

function must return http response

## Override the default exception handlers

By default, **Django Ninja** initialized the following exception handlers:


#### `ninja.errors.AuthenticationError`

Raised when authentication data is not valid

#### `ninja.errors.ValidationError`

Raised when request data does not validate

#### `ninja.errors.HttpError`

Used to throw http error with status code from any place of the code

#### `django.http.Http404`
 
 Django's default 404 exception (can be returned f.e. with `get_object_or_404`)

#### `Exception`
 
Any other unhandled exception by application.

Default behavior 
 
  - **if `settings.DEBUG` is `True`** - returns a traceback in plain text (useful when debugging in console or swagger UI)
  - **else** - default django exception handler mechanism is used (error logging, email to ADMINS)


### Override default handler

If you need to change default output for validation errors - override ValidationError exception handler:


```Python hl_lines="1 4"
from ninja.errors import ValidationError
...

@api.exception_handler(ValidationError)
def validation_errors(request, exc):
    return HttpResponse("Invalid input", status=422)
```


## Throwing HTTP responses with exceptions

As an alternative to custom exceptions and writing handlers for it - you can as well throw http exception that will lead to returning a http response with desired code


```Python
from ninja.errors import HttpError

@api.get("/some/resource")
def some_operation(request):
    if True:
        raise HttpError(503, "Service Unavailable. Please retry later.")

```
