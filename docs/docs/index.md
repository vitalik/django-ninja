# Django Ninja - Fast Django REST Framework

<div style="background-color: black; color: red; font-size: 16px; padding: 8px;">
 RUSSIA INVADED UKRAINE - <a href="https://github.com/vitalik/django-ninja/issues/383">Please read</a>
</div>


![Django Ninja](img/hero.png)

Django Ninja is a web framework for building APIs with Django and Python 3.6+ type hints.

Key features:

 - **Easy**: Designed to be easy to use and intuitive.
 - **FAST execution**: Very high performance thanks to **<a href="https://pydantic-docs.helpmanual.io" target="_blank">Pydantic</a>** and **<a href="guides/async-support/">async support</a>**. 
 - **Fast to code**: Type hints and automatic docs lets you focus only on business logic.
 - **Standards-based**: Based on the open standards for APIs: **OpenAPI** (previously known as Swagger) and **JSON Schema**.
 - **Django friendly**: (obviously) has good integration with the Django core and ORM.
 - **Production ready**: Used by multiple companies on live projects (If you use Django Ninja and would like to publish your feedback, please email ppr.vitaly@gmail.com).

<a href="https://github.com/vitalik/django-ninja-benchmarks" target="_blank">Benchmarks</a>:

![Django Ninja REST Framework](img/benchmark.png)

## Installation

```
pip install django-ninja
```

## Quick Example

Start a new Django project (or use an existing one)
```
django-admin startproject apidemo
```

in `urls.py`

```python hl_lines="3 5 8 9 10 15"
{!./src/index001.py!}
```

Now, run it as usual:
```
./manage.py runserver
```

Note: You don't have to add Django Ninja to your installed apps for it to work.

## Check it

Open your browser at <a href="http://127.0.0.1:8000/api/add?a=1&b=2" target="_blank">http://127.0.0.1:8000/api/add?a=1&b=2</a>

You will see the JSON response as:
```JSON
{"result": 3}
```
Now you've just created an API that:

 - receives an HTTP GET request at `/api/add`
 - takes, validates and type-casts GET parameters `a` and `b`
 - decodes the result to JSON
 - generates an OpenAPI schema for defined operation

## Interactive API docs

Now go to <a href="http://127.0.0.1:8000/api/docs" target="_blank">http://127.0.0.1:8000/api/docs</a>

You will see the automatic, interactive API documentation (provided by the <a href="https://github.com/swagger-api/swagger-ui" target="_blank">OpenAPI / Swagger UI</a> or <a href="https://github.com/Redocly/redoc" target="_blank">Redoc</a>):

![Swagger UI](img/index-swagger-ui.png)


## Recap

In summary, you declare the types of parameters, body, etc. **once only**, as function parameters. 

You do that with standard modern Python types.

You don't have to learn a new syntax, the methods or classes of a specific library, etc.

Just standard **Python 3.6+**.

For example, for an `int`:

```python
a: int
```

or, for a more complex `Item` model:

```python
class Item(Schema):
    foo: str
    bar: float

def operation(a: Item):
    ...
```

... and with that single declaration you get:

* Editor support, including:
    * Completion
    * Type checks
* Validation of data:
    * Automatic and clear errors when the data is invalid
    * Validation, even for deeply nested JSON objects
* <abbr title="also known as: serialization, parsing, marshalling">Conversion</abbr> of input data coming from the network, to Python data and types, and reading from:
    * JSON
    * Path parameters
    * Query parameters
    * Cookies
    * Headers
    * Forms
    * Files
* Automatic, interactive API documentation

This project was heavily inspired by <a href="https://fastapi.tiangolo.com/" target="_blank">FastAPI</a> (developed by <a href="https://github.com/tiangolo" target="_blank">Sebastián Ramírez</a>)

