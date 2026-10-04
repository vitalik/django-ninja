# Errors & Exception Handling

**Django Ninja** lets you install custom exception handlers to control exactly what response is returned when an exception is raised (or handled) inside a view.

## Default exception handlers

Out of the box, **Django Ninja** registers handlers for the following exceptions. Whenever one of these is raised anywhere in your view (or a dependency, like a resolver or auth callback), the matching handler builds the response automatically.

| Exception | Handler behavior |
|---|---|
| `ninja.errors.HttpError` | Returns `{"detail": <message>}` with the status code given to the exception. |
| `ninja.errors.ValidationError` | Returns `{"detail": <errors>}` with a `422` status. |
| `django.http.Http404` | Returns `{"detail": "Not Found"}` with a `404` status (includes exception details when `DEBUG=True`). |
| `Exception` (anything else) | If `settings.DEBUG` is `True`, returns a plain-text traceback with a `500` status. Otherwise, re-raises the exception so Django's normal error handling takes over (error logging, email to `ADMINS`, etc). |

`ninja.errors.AuthenticationError` and `ninja.errors.AuthorizationError` are both subclasses of `HttpError` (401 and 403 respectively), so they're handled by the `HttpError` handler unless you register something more specific. `AuthenticationError` is raised automatically by the [authentication](authentication.md) layer when a request fails to authenticate or an auth callback returns `False`; `AuthorizationError` isn't raised by Ninja itself — it's there for you to raise from inside a view or dependency when a permission check fails. `ninja.errors.Throttled` is also an `HttpError` subclass (429), raised by the [throttling](throttling.md) layer.

## Throwing HTTP errors

The simplest way to return an error response from inside a view is to raise `HttpError`:

```python
from ninja import NinjaAPI
from ninja.errors import HttpError

api = NinjaAPI()


@api.get("/some/resource")
def some_operation(request):
    if not request.user.is_staff:
        raise HttpError(503, "Service Unavailable. Please retry later.")
    return {"message": "Hello"}
```

`HttpError` takes a `status_code` and a `message`, and results in a `{"detail": message}` JSON response with that status.

## Custom exception handlers

For anything more involved than a plain `HttpError`, register a handler for your own exception class with `api.exception_handler`. This is useful, for example, when a view depends on an external service that's expected to be unavailable sometimes — instead of returning a generic `500`, you can catch it and return something friendlier.

```python hl_lines="8-9 12-18"
import random

from ninja import NinjaAPI

api = NinjaAPI()


class ServiceUnavailableError(Exception):
    pass


@api.exception_handler(ServiceUnavailableError)
def service_unavailable(request, exc):
    return api.create_response(
        request,
        {"message": "Please retry later"},
        status=503,
    )


@api.get("/service")
def some_operation(request):
    if random.choice([True, False]):
        raise ServiceUnavailableError()
    return {"message": "Hello"}
```

A handler function always takes two arguments:

- **`request`** — the Django `HttpRequest`
- **`exc`** — the raised exception instance

and must return an `HttpResponse`. `api.create_response()` is a convenience for building one that goes through the API's configured [renderer](renderers.md), but you can return any `HttpResponse` (or subclass) directly.

`exception_handler` is a thin wrapper over `api.add_exception_handler(exc_class, handler)`, which you can call directly instead of using it as a decorator.

!!! note "Handler lookup follows the MRO"
    When an exception is raised, Ninja walks the exception's class `__mro__` and uses the first registered handler it finds. So registering a handler for a base class also covers its subclasses — for example, overriding `HttpError` covers `AuthenticationError`, `AuthorizationError` and `Throttled` too, unless you also register something more specific for one of them.

## Overriding the default handlers

Because the built-ins above are just handlers registered for particular exception classes, you override any of them the same way — register your own handler for that class:

```python
from django.http import HttpResponse

from ninja import NinjaAPI
from ninja.errors import AuthenticationError

api = NinjaAPI()


@api.exception_handler(AuthenticationError)
def on_auth_error(request, exc):
    return HttpResponse("Please sign in", status=401)
```

## Customizing validation errors

Request validation failures raise `ninja.errors.ValidationError` (not to be confused with `pydantic.ValidationError`) and are handled by default with a `422` response shaped like:

```json
{
    "detail": [ ... ]
}
```

### Overriding the response shape

Override the `ValidationError` handler the same way as any other:

```python hl_lines="4 8-9"
from django.http import HttpResponse

from ninja import NinjaAPI
from ninja.errors import ValidationError

api = NinjaAPI()

@api.exception_handler(ValidationError)
def validation_errors(request, exc: ValidationError):
    return HttpResponse("Invalid input", status=422)
```

### Customizing the errors list itself

If you need more control over how validation errors are built — for example, referencing the schema tied to the field that failed — override `validation_error_from_error_contexts` on a `NinjaAPI` subclass instead. It receives a list of `ValidationErrorContext` objects (one per parameter source — path, query, body, etc. — that failed) and must return a `ValidationError`:

```python hl_lines="1 4 7-11"
from typing import Any

from ninja import NinjaAPI
from ninja.errors import ValidationError, ValidationErrorContext


class CustomNinjaAPI(NinjaAPI):
    def validation_error_from_error_contexts(
        self, error_contexts: list[ValidationErrorContext],
    ) -> ValidationError:
        custom_error_infos: list[dict[str, Any]] = []
        for context in error_contexts:
            model = context.model
            param_source = model.__ninja_param_source__
            for e in context.pydantic_validation_error.errors(
                include_url=False, include_context=False, include_input=False
            ):
                custom_error_infos.append(
                    {"loc": (param_source, *e["loc"]), "msg": e["msg"], "type": e["type"]}
                )
        return ValidationError(custom_error_infos)


api = CustomNinjaAPI()
```

Each `ValidationErrorContext` exposes:

- **`pydantic_validation_error`** — the underlying `pydantic.ValidationError`
- **`model`** — the `ParamModel` that failed validation, whose `__ninja_param_source__` tells you which part of the request it came from (`"path"`, `"query"`, `"body"`, etc.)

The `ValidationError` returned from `validation_error_from_error_contexts` is then passed through the normal `ValidationError` handler (default, or your own override), so both hooks can be combined.

## Unhandled exceptions

Anything that isn't caught by a registered handler falls through to the `Exception` handler:

- with `DEBUG=True`, the response is a `500` with a plain-text traceback — handy when debugging from the console or from Swagger UI
- with `DEBUG=False`, the exception is re-raised and handled by Django's normal machinery (500 page, error logging, admin emails, etc.)

You can override this too, for example to always return JSON instead of a traceback:

```python
import logging

from ninja import NinjaAPI

api = NinjaAPI()
logger = logging.getLogger("django")


@api.exception_handler(Exception)
def catch_all(request, exc: Exception):
    logger.exception(exc)
    return api.create_response(
        request,
        {"detail": "Internal server error"},
        status=500,
    )
```

Be careful overriding `Exception` globally — it will swallow errors you didn't anticipate too, so make sure logging still happens, as above.

!!! warning "Handlers are per-`NinjaAPI` instance"
    Exception handlers are registered on the `NinjaAPI` instance, not globally — `Router` has no `exception_handler` of its own. If you run multiple `NinjaAPI` instances, each needs its own `exception_handler` registrations.
