<a href="https://github.com/vitalik/django-ninja/issues/383"><img width="814" alt="SCR-20230123-m1t" src="https://user-images.githubusercontent.com/95222/214056666-585c0479-c122-4cb3-add4-b8844088ccdd.png"></a>



<a href="https://github.com/vitalik/django-ninja/issues/383">^ Please read ^</a>




<p align="center">
  <a href="https://django-ninja.dev/"><img src="https://django-ninja.dev/img/logo-big.png"></a>
</p>
<p align="center">
    <em>Fast to learn, fast to code, fast to run</em>
</p>


![Test](https://github.com/vitalik/django-ninja/actions/workflows/test_full.yml/badge.svg)
![Coverage](https://img.shields.io/codecov/c/github/vitalik/django-ninja)
[![PyPI version](https://badge.fury.io/py/django-ninja.svg)](https://badge.fury.io/py/django-ninja)
[![Downloads](https://static.pepy.tech/personalized-badge/django-ninja?period=month&units=international_system&left_color=black&right_color=brightgreen&left_text=downloads/month)](https://pepy.tech/project/django-ninja)

# Django Ninja - Fast Django REST Framework

**Django Ninja** is a web framework for building APIs with **Django** and Python 3.6+ **type hints**.


 **Key features:**

  - **Easy**: Designed to be easy to use and intuitive.
  - **FAST execution**: Very high performance thanks to **<a href="https://pydantic-docs.helpmanual.io" target="_blank">Pydantic</a>** and **<a href="/docs/docs/guides/async-support.md">async support</a>**.
  - **Fast to code**: Type hints and automatic docs lets you focus only on business logic.
  - **Standards-based**: Based on the open standards for APIs: **OpenAPI** (previously known as Swagger) and **JSON Schema**.
  - **Django friendly**: (obviously) has good integration with the Django core and ORM.
  - **Production ready**: Used by multiple companies on live projects (If you use django-ninja and would like to publish your feedback, please email ppr.vitaly@gmail.com).



![Django Ninja REST Framework](docs/docs/img/benchmark.png)

**Documentation**: https://django-ninja.dev

---

## Installation

```
pip install django-ninja
```



## Usage


In your django project next to urls.py create new `api.py` file:

```Python
from ninja import NinjaAPI

api = NinjaAPI()


@api.get("/add")
def add(request, a: int, b: int):
    return {"result": a + b}
```


Now go to `urls.py` and add the following:


```Python hl_lines="3 7"
...
from .api import api

urlpatterns = [
    path("admin/", admin.site.urls),
    path("api/", api.urls),  # <---------- !
]
```

**That's it !**

Now you've just created an API that:

 - receives an HTTP GET request at `/api/add`
 - takes, validates and type-casts GET parameters `a` and `b`
 - decodes the result to JSON
 - generates an OpenAPI schema for defined operation

### Interactive API docs

Now go to <a href="http://127.0.0.1:8000/api/docs" target="_blank">http://127.0.0.1:8000/api/docs</a>

You will see the automatic interactive API documentation (provided by <a href="https://github.com/swagger-api/swagger-ui" target="_blank">Swagger UI</a> or <a href="https://github.com/Redocly/redoc" target="_blank">Redoc</a>):


![Swagger UI](docs/docs/img/index-swagger-ui.png)

## What next?

 - Read the full documentation here - https://django-ninja.dev
 - To support this project, please give star it on Github. ![github star](docs/docs/img/github-star.png)
 - Share it [via Twitter](https://twitter.com/intent/tweet?text=Check%20out%20Django%20Ninja%20-%20Fast%20Django%20REST%20Framework%20-%20https%3A%2F%2Fdjango-ninja.dev)
 - If you already using django-ninja, please share your feedback to ppr.vitaly@gmail.com
