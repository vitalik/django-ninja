# Handling errors

**Django Ninja** allows you to install custom exception handlers to deal with how you return responses when errors or handled exceptions occur.

## Custom exception handlers

Let's say you are making API that depends on some external service that is designed to be unavailable at some moments. Instead of throwing default 500 error upon exception - you can handle the error and give some friendly response back to the client (to come back later)

To achieve that you need:

1. create some exception (or use existing one)
2. use api.exception_handler decorator


Example:


```python hl_lines="9 10"
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

**Django Ninja** registers default exception handlers for the types shown below.
You can register your own handlers with `@api.exception_handler` to override the default handlers.

#### `ninja.errors.AuthenticationError`

Raised when authentication data is not valid

#### `ninja.errors.AuthorizationError`

Raised when authentication data is valid, but doesn't allow you to access the resource

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


## Customizing request validation errors

Requests that fail validation raise `ninja.errors.ValidationError` (not to be confused with `pydantic.ValidationError`).
`ValidationError`s have a default exception handler that returns a 422 (Unprocessable Content) JSON response of the form:
```json
{
    "detail": [ ... ]
}
```

You can change this behavior by overriding the default handler for `ValidationError`s:

```python hl_lines="1 4"
from ninja.errors import ValidationError
...

@api.exception_handler(ValidationError)
def validation_errors(request, exc):
    return HttpResponse("Invalid input", status=422)
```

If you need even more control over validation errors (for example, if you need to reference the schema associated with
the model that failed validation), you can supply your own `validation_error_from_error_contexts` in a `NinjaAPI` subclass:

```python hl_lines="4"
from ninja.errors import ValidationError, ValidationErrorContext
from typing import Any, Dict, List

class CustomNinjaAPI(NinjaAPI):
    def validation_error_from_error_contexts(
        self, error_contexts: List[ValidationErrorContext],
    ) -> ValidationError:
        custom_error_infos: List[Dict[str, Any]] = []
        for context in error_contexts:
            model = context.model
            pydantic_schema = model.__pydantic_core_schema__
            param_source = model.__ninja_param_source__
            for e in context.pydantic_validation_error.errors(
                include_url=False, include_context=False, include_input=False
            ):
                custom_error_info = {
                # TODO: use `e`, `param_source`, and `pydantic_schema` as desired
                }
                custom_error_infos.append(custom_error_info)
        return ValidationError(custom_error_infos)

api = CustomNinjaAPI()
```

Now each `ValidationError` raised during request validation will contain data from your `validation_error_from_error_contexts`.


## Throwing HTTP responses with exceptions

As an alternative to custom exceptions and writing handlers for it - you can as well throw http exception that will lead to returning a http response with desired code


```python
from ninja.errors import HttpError

@api.get("/some/resource")
def some_operation(request):
    if True:
        raise HttpError(503, "Service Unavailable. Please retry later.")

```
