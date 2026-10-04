# Tutorial - Parsing Input

## Input from the query string

Let's change our operation to accept a name from the URL's query string. To do that, just add a `name` argument to our function.

```python
@api.get("/hello")
def hello(request, name):
    return f"Hello {name}"
```

When we provide a name argument, we get the expected (HTTP 200) response.

<a href="http://localhost:8000/api/hello?name=you"
target="_blank">localhost:8000/api/hello?name=you</a>:

```json
"Hello you"
```

### Defaults

Not providing the argument will return an HTTP 422 error response.

*[HTTP 422]: Unprocessable Entity

<a href="http://localhost:8000/api/hello"
target="_blank">localhost:8000/api/hello</a>:

```json
{
  "detail": [
    {
      "loc": ["query", "name"],
      "msg": "field required",
      "type": "value_error.missing"
    }
  ]
}
```

We can specify a default for the `name` argument in case it isn't provided:

```python hl_lines="2"
@api.get("/hello")
def hello(request, name="world"):
    return f"Hello {name}"
```

## Input types

**Django Ninja** uses standard [Python type hints](https://docs.python.org/3/library/typing.html) to format the input types. If no type is provided then a string is assumed (but it is good practice to provide type hints for all your arguments).

Let's add a second operation that does some basic math with integers.

```python hl_lines="5-7"
@api.get("/hello")
def hello(request, name: str = "world"):
    return f"Hello {name}"

@api.get("/math")
def math(request, a: int, b: int):
    return {"add": a + b, "multiply": a * b}
```

<a href="http://localhost:8000/api/math?a=2&b=3"
target="_blank">localhost:8000/api/math?a=2&b=3</a>:

```json
{
  "add": 5,
  "multiply": 6
}
```

## Input from the path

You can declare path "parameters" with the same syntax used by Python format-strings.

Any parameters found in the path string will be passed to your function as arguments, rather than expecting them from the query string.

```python hl_lines="1"
@api.get("/math/{a}and{b}")
def math(request, a: int, b: int):
    return {"add": a + b, "multiply": a * b}
```

Now we access the math operation from <a href="http://localhost:8000/api/math/2and3"
target="_blank">localhost:8000/api/math/2and3</a>.


## Input from the request body

We are going to change our `hello` operation to use HTTP `POST` instead, and take arguments from the request body.

To specify that arguments come from the body, we need to declare a Schema.

*[Schema]: An extension of a Pydantic "Model"

```python hl_lines="1 5-6 8-10"
from ninja import NinjaAPI, Schema

api = NinjaAPI()

class HelloSchema(Schema):
    name: str = "world"

@api.post("/hello")
def hello(request, data: HelloSchema):
    return f"Hello {data.name}"
```

### Self-documenting API

Accessing <a href="http://localhost:8000/api/hello" target="_blank">localhost:8000/api/hello</a> now results in a HTTP 405 error response, since we need to POST to this URL instead.

*[HTTP 405]: Method Not Allowed

An easy way to do this is to use the Swagger documentation that is automatically created for us, at default URL of "/docs" (appended to our API url root).

1. Visit <a href="http://localhost:8000/api/docs" target="_blank">localhost:8000/api/docs</a> to see the operations we have created
1. Open the `/api/hello` operation
2. Click "Try it out"
3. Change the request body
4. Click "Execute"

!!! success

    Continue on to **[Handling responses](step3.md)**