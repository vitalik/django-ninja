# Django Ninja - Fast Django REST Framework

![Django Ninja](img/hero.png)

Django Ninja is a web framework for building APIs with Django and Python 3.6+ based type hints.

Key features

 - **Easy**: Designed to be easy to use and intuitive.
 - **Fast**: Very high performance thanks to Pydantic and **<a href="/async-support/">async support</a>**. 
 - **Fast to code**: Type hints and automatic docs let's you focus only on business logic.
 - **Standards-based**: Based on the open standards for APIs: **OpenAPI** (previously known as Swagger) and **JSON Schema**.
 - **Django friendly**: (obviously) have good integration with Django core an ORM.

<a href="https://github.com/vitalik/django-ninja-benchmarks" target="_blank">Benchmarks</a>:

![Django Ninja REST Framework](img/benchmark.png)

## Installation

```
pip install django-ninja
```

## Quick Example

Start a new django project (or use existing)
```
django-admin startproject apidemo
```

in `urls.py`

```Python hl_lines="3 5 8 9 10 15"
{!./src/index001.py!}
```

Now, run it as usual:
```
./manage.py runserver
```

## Check it

Open your browser at <a href="http://127.0.0.1:8000/api/add?a=1&b=2" target="_blank">http://127.0.0.1:8000/api/add?a=1&b=2</a>

You will see the JSON response as:
```JSON
{"result": 3}
```
You already created an API that:

 - Receives HTTP GET request at `/api/add`
 - Takes, validates and type-casts GET parameters `a` and `b`
 - Decodes to JSON operation result
 - Generates an OpenAPI schema for defined operation

## Interactive API docs

Now go to <a href="http://127.0.0.1:8000/api/docs" target="_blank">http://127.0.0.1:8000/api/docs</a>

You will see the automatic interactive API documentation (provided by <a href="https://github.com/swagger-api/swagger-ui" target="_blank">Swagger UI</a>):


![Swagger UI](img/index-swagger-ui.png)


## Recap

In summary, you declare **once** the types of parameters, body, etc. as function parameters. 

You do that with standard modern Python types.

You don't have to learn a new syntax, the methods or classes of a specific library, etc.

Just standard **Python 3.6+**.

For example, for an `int`:

```Python
a: int
```

or for a more complex `Item` model:

```Python
class Item(Schema):
    foo: str
    bar: float

def operation(a: Item):
    ...
```

...and with that single declaration you get:

* Editor support, including:
    * Completion.
    * Type checks.
* Validation of data:
    * Automatic and clear errors when the data is invalid.
    * Validation even for deeply nested JSON objects.
* <abbr title="also known as: serialization, parsing, marshalling">Conversion</abbr> of input data: coming from the network to Python data and types. Reading from:
    * JSON.
    * Path parameters.
    * Query parameters.
    * Cookies.
    * Headers.
    * Forms.
    * Files.
* Automatic interactive API documentation

This project was heavily inspired by <a href="https://fastapi.tiangolo.com/" target="_blank">FastAPI</a> (developed by <a href="https://github.com/tiangolo" target="_blank">Sebastián Ramírez</a>)

