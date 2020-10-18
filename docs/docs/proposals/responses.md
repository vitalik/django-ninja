# Multiple Response Schemas


!!! warning ""
    This is just a proposal and it is **not present in library code**. But eventually this can be a part of Django Ninja.

    Please consider adding likes/dislikes or comments in [github issue](https://github.com/vitalik/django-ninja/issues/16) to express your feeling about this proposal


## Problem

Currently you can define a response schema via `response` argument:

```Python hl_lines="6"
class Token(Schema):
    token: str
    expires: date


@api.post('/login', response=Token)
def login(request, payload: Auth):
    ...
    return {'token': 'secret', 'expires': date(2025, 12, 13)}
```

This will define that login operation can only return one type of response with `{token: xxx, expires: yyy}`

But sometimes you need to define more then response schemas. Like when in case of authentication you can return
 - 200 successful -> token
 - 401 -> Unauthorized
 - 402 -> Payment required
 - etc..

In fact the [OpenAPI specification](https://swagger.io/docs/specification/describing-responses/) allows to pass multiple response schemas


## Solution

### 1) Via Union type hint

```Python hl_lines="1 11"
from typing import Union

class Token(Schema):
    token: str
    expires: date

class Message(Schema):
    message: str


@api.post('/login', response=Union[Token, Message])
def login(request, payload: Auth):
    if auth_not_valid:
        return {'message': 'Unauthorized'}
    return {'token': xxx, ...}
```

 - **Pros**: simplicity and type-hints
 - **Cons**: not possible to output http status code (or define via openapi schema)

### 2) Via response dictionary

```Python hl_lines="9 12 14 16"
class Token(Schema):
    token: str
    expires: date

class Message(Schema):
    message: str


@api.post('/login', response={200: Token, 401: Message, 402: Message})
def login(request, payload: Auth):
    if auth_not_valid:
        return 401, {'message': 'Unauthorized'}
    if negative_balance:
        return 402, {'message': 'Insufficient balance amount. Please proceed to a payment page.'}
    return 200, {'token': xxx, ...}
```
 - **Pros**: 
    - Can return different http codes
    - Fully compatible with Open api schema
 - **Cons**:
    - Have to always return a status code number to mark which schema is outputting


## Naming issues

`response` seems a very generic name, maybe better use something like `response_schemas` (but seems to long), please give your thoughts on naming.

## Your thoughts/proposals

Please give you thoughts/likes/dislikes about this proposal in the [github issue](https://github.com/vitalik/django-ninja/issues/16)