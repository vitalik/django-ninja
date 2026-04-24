# Request Header

Django Ninja provides a convenient `Header()` parameter function to extract values from HTTP request headers in your API endpoints.

## Usage Patterns

There are two main ways to work with headers:

### 1. Custom Header Name

!!! note
    Use the `alias` parameter to specify the exact HTTP header name (with hyphens)
    Do NOT use underscores in the parameter name, as Python identifiers cannot contain hyphens.

- Python 3.6+ non-Annotated

```python hl_lines="5"
{!./src/tutorial/header/code01.py!}
```

- Python 3.9+ Annotated

```python hl_lines="5 9"
{!./src/tutorial/header/code02.py!}
```

This pattern is ideal for:
- Custom headers (e.g., `X-API-Key`, `X-Request-ID`)
- Non-standard header names
- When you want explicit control over header mapping

### 2. Well-Known Headers

For common HTTP headers, you can use snake_case parameter names without an alias:

```python hl_lines="5 11 19 23"
{!./src/tutorial/header/code03.py!}
```

Common implicit headers include:

- `user_agent` → `User-Agent`
- `content_length` → `Content-Length`
- `content_type` → `Content-Type`
- `authorization` → `Authorization`
- etc.
