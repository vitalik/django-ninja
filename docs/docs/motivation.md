# Motivation

!!! quote
    **Django Ninja** looks basically the same as **FastAPI**. So, why not just FastAPI?

Indeed **Django Ninja** is heavily inspired by <a href="https://fastapi.tiangolo.com/" target="_blank">FastAPI</a> (developed by <a href="https://github.com/tiangolo" target="_blank">Sebastián Ramírez</a>)

But there are few issues when it comes to join FastAPI and Django

1) **FastAPI** declares to be ORM agnostic (meaning you can use it with SqlAlchemy or DjangoORM). But in reality Django ORM is not yet ready for async use (will be in version 3.2). And if you use it in sync mode - you can have a [closed connection issue](https://github.com/tiangolo/fastapi/issues/716) which you will have to overcome with lot's of crunches.

2) The dependency injection with arguments makes your code too much verbose when you rely on authentication and database session in your operations (which for some projects makes it like 99% of all operations)

```Python hl_lines="25 26"
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

3) Since word `model` in django is "reserved" for ORM = it becomes very unclear when you mix django orm into Pydantic/FastAPI model naming convention. 

### Django Ninja

Django Ninja addresses all those issues and includes a great integration with Django (ORM, urls, views, auth and more...)

#### Main Features

1) Since you can have multiple NinjaAPI instances - you can run [multiple API versions](/tutorial/versioning) inside one django project

```Python
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

2) Django Ninja Schema - is integrated with ORM so you [can serialize querysets](/tutorial/response-schema/#returning-querysets) or ORM objects:

```Python
@api.get("/tasks", response=List[TaskSchema])
def tasks(request):
    return Task.objects.all()


@api.get("/tasks", response=TaskSchema)
def tasks_details(request):
    task = Task.objects.first()
    return task
```
3) Soon you should be able to [create Schema's from Django Models](/proposals/models/)

4) Instead of dependency arguments **Django Ninja** uses `request` instance attributes (same way as regular django views) - see more details on [Authentication](/tutorial/authentication/)
