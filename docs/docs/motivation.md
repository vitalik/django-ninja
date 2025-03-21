# Motivation

!!! quote
    **Django Ninja** looks basically the same as **FastAPI**, so why not just use FastAPI?

Indeed, **Django Ninja** is heavily inspired by <a href="https://fastapi.tiangolo.com/" target="_blank">FastAPI</a> (developed by <a href="https://github.com/tiangolo" target="_blank">Sebastián Ramírez</a>)

That said, there are few issues when it comes to getting FastAPI and Django to work together properly:

1) **FastAPI** declares to be ORM agnostic (meaning you can use it with SQLAlchemy or the Django ORM), but in reality the Django ORM is not yet ready for async use (it may be in version 4.0 or 4.1), and if you use it in sync mode, you can have a [closed connection issue](https://github.com/tiangolo/fastapi/issues/716) which you will have to overcome with a **lot** of effort.

2) The dependency injection with arguments makes your code too verbose when you rely on authentication and database sessions in your operations (which for some projects is about 99% of all operations).

```python hl_lines="25 26"
...

app = FastAPI()


# Dependency
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


async def get_current_user(token: str = Depends(oauth2_scheme)):
    user = decode(token)
    if not user:
        raise HTTPException(...)
    return user


@app.get("/task/{task_id}", response_model=Task)
def read_user(
        task_id: int,
        db: Session = Depends(get_db), 
        current_user: User = Depends(get_current_user),
    ):
        ... use db with current_user ....
```

3) Since the word `model` in Django is "reserved" for use by the ORM, it becomes very confusing when you mix the Django ORM with Pydantic/FastAPI model naming conventions. 

### Django Ninja

Django Ninja addresses all those issues, and integrates very well with Django (ORM, urls, views, auth and more)

Working at [Code-on a Django webdesign webedevelopment studio](https://code-on.be/) I get all sorts of challenges and to solve these I started Django-Ninja in 2020.

Note: **Django Ninja is a production ready project** - my estimation is at this time already 100+ companies using it in production and 500 new developers joining every month. 

Some companies are already looking for developers with django ninja experience.

#### Main Features

1) Since you can have multiple Django Ninja API instances - you can run [multiple API versions](guides/versioning.md) inside one Django project.

```python
api_v1 = NinjaAPI(version='1.0', auth=token_auth)
...
api_v2 = NinjaAPI(version='2.0', auth=token_auth)
...
api_private = NinjaAPI(auth=session_auth, urls_namespace='private_api')
...


urlpatterns = [
    ...
    path('api/v1/', api_v1.urls),
    path('api/v2/', api_v2.urls),
    path('internal-api/', api_private.urls),
]
```

2) The Django Ninja 'Schema' class is integrated with the ORM, so you can [serialize querysets](guides/response/index.md#returning-querysets) or ORM objects:

```python
@api.get("/tasks", response=List[TaskSchema])
def tasks(request):
    return Task.objects.all()


@api.get("/tasks", response=TaskSchema)
def tasks_details(request):
    task = Task.objects.first()
    return task
```
3) [Create Schema's from Django Models](guides/response/django-pydantic.md).

4) Instead of dependency arguments, **Django Ninja** uses `request` instance attributes (in the same way as regular Django views) - more detail at [Authentication](guides/authentication.md).
