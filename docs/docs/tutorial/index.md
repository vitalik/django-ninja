# Tutorial - Intro

This tutorial shows you how to use **NinjaAPI** with most of its features. 
It is also built to work as a reference documentation.
So you can come back and see exactly what you need.

This tutorial assumes that you know at least some basics of the <a href="https://www.djangoproject.com/" target="_blank">Django Framework</a> like how to create a project and run it.


## Installation

```
pip install django-ninja
```


## Create django project

(if you already have existing django project - skip to the next step)

Start a new django project (or use existing).

```
django-admin startproject myproject
```


## First steps

Let's create a module for our API - create an **api.py** file next to **urls.py**:


`api.py`


```Python
from ninja import NinjaAPI

api = NinjaAPI()


@api.get("/hello")
def hello(request):
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

"Operation" can be one of the HTTP "methods".

 - GET
 - POST
 - PUT
 - DELETE
 - PATCH
 - ... and more


Django Ninja comes with a decorator for each method:


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

if you need to handle multiple methods with single function you can use api


```Python hl_lines="1"
@api.api_operation(["POST", "PATCH"])
def mixed(request):
    ...
```