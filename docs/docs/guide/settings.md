# Settings

Django Ninja reads a small number of `NINJA_*` settings from your Django
`settings.py`. All of them are optional — every setting has a built-in
default, so a project with no `NINJA_*` settings at all behaves exactly like
one that sets them all explicitly to their defaults.

## How it works

Settings are collected once, at import time, into a `pydantic` model
(`ninja.conf.settings`), which validates and coerces the values from
`django.conf.settings`:

```python
from ninja.conf import settings

settings.PAGINATION_PER_PAGE  # 100
```

Because it's a `pydantic` model, values are type-checked and coerced when
they're loaded — setting `NINJA_PAGINATION_PER_PAGE = "20"` in `settings.py`
works the same as `20`, but `NINJA_PAGINATION_PER_PAGE = "not a number"`
raises a validation error.

!!! tip "Overriding in tests"
    `ninja.conf` listens for Django's `setting_changed` signal, so
    `@override_settings(NINJA_PAGINATION_PER_PAGE=5)` (or `settings()` as a
    context manager) works as expected in tests — the change is picked up
    immediately and reverted when the override ends. Only settings whose
    name starts with `NINJA_` trigger a refresh.

## All settings

| Setting | Default | Used by |
|---|---|---|
| `NINJA_PAGINATION_CLASS` | `"ninja.pagination.LimitOffsetPagination"` | [`@paginate`](pagination.md) with no explicit class |
| `NINJA_PAGINATION_PER_PAGE` | `100` | Default page size for all three built-in pagination classes |
| `NINJA_MAX_PER_PAGE_SIZE` | `100` | Upper bound on a client-supplied `page_size` for `PageNumberPagination`/`CursorPagination` |
| `NINJA_PAGINATION_MAX_OFFSET` | `100` | Upper bound on the internal offset a `CursorPagination` cursor can encode |
| `NINJA_PAGINATION_MAX_LIMIT` | unbounded (`inf`) | Upper bound on `limit` for `LimitOffsetPagination` |
| `NINJA_PAGINATION_DEFAULT_ORDERING` | `("-pk",)` | Default `ordering` for `CursorPagination` |
| `NINJA_DEFAULT_THROTTLE_RATES` | `{"auth": "10000/day", "user": "10000/day", "anon": "1000/day"}` | Rate used by a built-in [throttle](throttling.md) instantiated without one |
| `NINJA_NUM_PROXIES` | `None` | Number of trusted proxies `AnonRateThrottle`/friends skip in `X-Forwarded-For` |
| `NINJA_FIX_REQUEST_FILES_METHODS` | `{"PUT", "PATCH", "DELETE"}` | Methods the [file-upload compatibility middleware](files.md#requestfiles-with-put-and-patch) covers |

!!! note
    `NINJA_MAX_PER_PAGE_SIZE` is the odd one out — the underlying Python
    attribute is `PAGINATION_MAX_PER_PAGE_SIZE`, but the Django setting name
    drops `PAGINATION_` from the middle. Every other setting's name is its
    attribute name with a `NINJA_` prefix.

## Pagination settings

```python
# settings.py
NINJA_PAGINATION_CLASS = "ninja.pagination.LimitOffsetPagination"
NINJA_PAGINATION_PER_PAGE = 100
NINJA_MAX_PER_PAGE_SIZE = 100
NINJA_PAGINATION_MAX_OFFSET = 100
NINJA_PAGINATION_MAX_LIMIT = 1000
NINJA_PAGINATION_DEFAULT_ORDERING = ("-pk",)
```

- **`NINJA_PAGINATION_CLASS`** — the class `@paginate` uses when applied
  without an explicit class (`@paginate` vs. `@paginate(PageNumberPagination)`).
- **`NINJA_PAGINATION_PER_PAGE`** — default `page_size`/`limit` when the
  client doesn't supply one, for any of the three built-in classes.
- **`NINJA_MAX_PER_PAGE_SIZE`** — caps a client-supplied `page_size` for
  `PageNumberPagination` and `CursorPagination` (`LimitOffsetPagination` has
  no such cap on `limit` — see `NINJA_PAGINATION_MAX_LIMIT` below).
- **`NINJA_PAGINATION_MAX_OFFSET`** — safeguards `CursorPagination`: it
  bounds the internal offset a cursor can encode, so a malicious cursor
  value can't force an unbounded skip.
- **`NINJA_PAGINATION_MAX_LIMIT`** — caps the `limit` query parameter
  accepted by `LimitOffsetPagination`. Unset, a client can request an
  unbounded `limit`.
- **`NINJA_PAGINATION_DEFAULT_ORDERING`** — the `ordering` `CursorPagination`
  uses when the operation doesn't pass its own.

See [Pagination](pagination.md) for how each class uses these.

## Throttling settings

```python
# settings.py
NINJA_DEFAULT_THROTTLE_RATES = {
    "auth": "10000/day",
    "user": "10000/day",
    "anon": "1000/day",
}
NINJA_NUM_PROXIES = 1
```

- **`NINJA_DEFAULT_THROTTLE_RATES`** — the rate `AnonRateThrottle()`,
  `UserRateThrottle()` and `AuthRateThrottle()` fall back to when
  instantiated without a `rate` argument, keyed by throttle `scope`
  (`"anon"`, `"user"`, `"auth"`).
- **`NINJA_NUM_PROXIES`** — the number of trusted reverse proxies in front
  of your API. `AnonRateThrottle` and the IP-fallback path of the other
  throttles use it to pick the real client address out of
  `X-Forwarded-For`. Left as `None` (the default), the whole header is used
  as-is.

See [Throttling](throttling.md#default-rates-per-scope) for details and
custom throttle classes.

## File upload settings

```python
# settings.py
NINJA_FIX_REQUEST_FILES_METHODS = {"PUT", "PATCH"}
```

- **`NINJA_FIX_REQUEST_FILES_METHODS`** — the HTTP methods for which Django
  Ninja's compatibility middleware
  (`ninja.compatibility.files.fix_request_files_middleware`) parses
  `multipart/form-data` and populates `request.FILES`. Django only does this
  for `POST` by default, so file parameters on other methods need either the
  middleware or a narrower/wider set here. See
  [File Uploads](files.md#requestfiles-with-put-and-patch) for the full
  explanation and setup.

## Removed settings

`NINJA_DOCS_VIEW` was removed — setting it raises an exception at startup.
Pass `docs=` to `NinjaAPI(...)` instead; see
[OpenAPI & Interactive Docs](openapi.md).
