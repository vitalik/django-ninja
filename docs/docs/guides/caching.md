# Caching

**Django Ninja** has a simple method for caching utilizing [Django's low level caching mechanism](https://docs.djangoproject.com/en/dev/topics/cache/#the-low-level-cache-api).

*This assumes caching and supporting infrastructure (e.g. redis, memcache etc.) is set up and configured correctly in Django setttings.*

## Caching methodology

Django caching pickles the payload before saving it to the cache. 

From the [Django Docs](https://docs.djangoproject.com/en/dev/topics/cache/#the-low-level-cache-api):
> You can cache any Python object that can be pickled safely: strings, dictionaries, lists of model objects, and so forth. (Most common Python objects can be pickled; refer to the Python documentation for more information about pickling.)

One can use the **Django Ninja** `schema.from_orm()` method to safely convert a queryset to a pickle-safe object.

### How to cache a request

Suppose one has the following very expensive query (time/cpu/db intensive) endpoints:

```Python
class TaskSchema(Schema):
    id: int
    title: str
    is_completed: bool
    owner: Optional[str]
    lower_title: str

    @staticmethod
    def resolve_owner(obj):
        if not obj.owner:
            return
        return f"{obj.owner.first_name} {obj.owner.last_name}"

    def resolve_lower_title(self, obj):
        return self.title.lower()

@api.get("/task/{id}", response=TaskSchema)
def get_task(request, id: int):
    return Task.objects.get(pk=id)

@api.get("/tasks", response=List[TaskSchema])
def tasks(request):
    return Task.objects.all()
```


By slightly changing the endpoint and utilizing Schema `from_orm()` method, standard Django caching can be implemented:

```Python
from django.core.cache import cache # don't forget import!

@api.get("/task/{id}") # remove response to default ninja to JsonResponse
def get_task(request, id: int):
    c = cache.get(f"task_{id}", None)
    if c is None:
        qs = Task.objects.get(pk=id)
        c = TaskSchema.from_orm(qs).dict()
        cache.set(f"task_{id}", c) # assumes default timeout
    return c

@api.get("/tasks", response=List[TaskSchema])# remove response to default ninja to JsonResponse
def tasks(request):
    c = cache.get("all_tasks", None)
    if c is None:
        qs = Task.objects.all()
        c = [TaskSchema.from_orm(i).dict() for i in qs]
        cache.set("all_tasks", c) # assumes default timeout
    return c

```