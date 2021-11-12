# Tutorial - Intro

This tutorial shows you how to use **Django Ninja** with most of its features. 
It is also built to work as reference documentation.

This tutorial assumes that you know at least some basics of the <a href="https://www.djangoproject.com/" target="_blank">Django Framework</a>, like how to create a project and run it.


## Installation

```
pip install django-ninja
```

!!! note
    It is not required, but you can also put `ninja` to `INSTALLED_APPS`.
    In that case the OpenAPI/Swagger UI will be loaded (faster) from the included JavaScript bundle (otherwise the JavaScript bundle comes from a CDN).


## Create a Django project

(If you already have an existing Django project, skip to the next step).

Start a new Django project (or use an existing one).

```
django-admin startproject myproject
```


## First steps

Let's create a module for our API.  Create an **api.py** file in the same directory location as **urls.py**:


`api.py`


```Python
from ninja import NinjaAPI

api = NinjaAPI()


@api.get("/hello")
def hello():
    return "Hello world"

```

Now go to **urls.py** and add the following:


```Python hl_lines="3 7"
from django.contrib import admin
from django.urls import path
from .api import api

urlpatterns = [
    path("admin/", admin.site.urls),
    path("api/", api.urls),
]
```

## Defining operation methods

"Operation" can be one of the HTTP "methods":

 - GET
 - POST
 - PUT
 - DELETE
 - PATCH
 - ... and more


**Django Ninja** comes with a decorator for each method:


```Python hl_lines="1 5 9 13 17"
@api.get("/path")
def get_operation(request):
    ...

@api.post("/path")
def post_operation(request):
    ...

@api.put("/path")
def put_operation(request):
    ...

@api.delete("/path")
def delete_operation(request):
    ...

@api.patch("/path")
def patch_operation(request):
    ...
```

If you need to handle multiple methods with a single function, you can use the `api_operation` method:


```Python hl_lines="1"
@api.api_operation(["POST", "PATCH"])
def mixed(request):
    ...
```

## Passing the request object to the view

Passing the request object to a view is optional.

```python hl_lines="2"
@api.get("/hello")
def hello():
    return "Hello world"
```

If passing in the request object is required it must be the first parameter.

```python hl_lines="2"
@api.get("/hello")
def hello(request, user_name="World"):
    return f"Hello {user_name}"
```

If the request object needs to be named something other than `request`, it must be typed
as `django.http.HttpRequest` or one of its subclasses.


```python hl_lines="4"
from django.http import HttpRequest

@api.get("/hello")
def hello(a_param_not_named_request: HttpRequest, user_name="World"):
    return f"Hello {user_name}"
```

!!! warning
    Decorators may expect the request object to be passed into the view function.  If the
    request is not present in decorated view's signature, the request will not be passed
    to the view function, and may cause some hard to debug errors.
