# Class Based Operations


!!! warning ""
    This is just a proposal and it is **not present in library code**. But eventually this can be a part of Django Ninja.

    Please consider adding likes/dislikes or comments in [github issue](https://github.com/vitalik/django-ninja/issues/15) to express your feeling about this proposal


## Problem

An API operation is a callable which takes a request and parameters and returns a response. 
But it is often a case in real world when you need to reuse same pieces of code in multiple operations.

Let's take the following example:

 - We have a TODO application with Projects and Tasks
 - Each project have multiple tasks
 - and as well each project may have an owner(user)
 - other users should not be able to access project they not owe

Model structure is something like this:

```Python
class Project(models.Model):
    title = models.CharField(max_length=100)
    owner = models.ForeignKey('auth.User', on_delete=models.CASCADE)

class Task(models.Model):
    project = models.ForeignKey(Project, on_delete=models.CASCADE)
    title = models.CharField(max_length=100)
    completed = models.BooleanField()
```


Let's now create few API operations for it:

 - list of tasks for project
 - task details
 - complete task action

All should validate that user can only access his/her project's tasks (otherwise return 404)

It can be something like this:


```Python
router = Router()

@router.get('/project/{project_id}/tasks/', response=List[TaskOut])
def task_list(request):
    user_projects = request.user.project_set
    project = get_object_or_404(user_projects, id=project_id))
    return project.task_set.all()

@router.get('/project/{project_id}/tasks/{task_id}/', response=TaskOut)
def details(request, task_id: int):
    user_projects = request.user.project_set
    project = get_object_or_404(user_projects, id=project_id))
    user_tasks = project.task_set.all()
    return get_object_or_404(user_tasks, id=task_id)


@router.post('/project/{project_id}/tasks/{task_id}/complete', response=TaskOut)
def complete(request, task_id: int):
    user_projects = request.user.project_set
    project = get_object_or_404(user_projects, id=project_id))
    user_tasks = project.task_set.all()
    task = get_object_or_404(user_tasks, id=task_id)
    task.completed = True
    task.save()
    return task
```


As you can see - these lines are getting repeated pretty often to check permission:

```Python hl_lines="1 2 "
user_projects = request.user.project_set
project = get_object_or_404(user_projects, id=project_id))
```

You can extract it to a function, but it will just make it 3 lines smaller and still be pretty polluted...


## Solution

The proposal is to have alternative called "Class Based Operation" where you can decorate with `path` decorator entire class:


```Python hl_lines="7 8"
from ninja import Router


router = Router()


@router.path('/project/{project_id}/tasks')
class Tasks:

    def __init__(self, request, project_id=int):
        user_projects = request.user.project_set
        self.project = get_object_or_404(user_projects, id=project_id))
        self.tasks = self.project.task_set.all()
    

    @router.get('/', response=List[TaskOut])
    def task_list(self, request):
        return self.tasks

    @router.get('/{task_id}/', response=TaskOut)
    def details(self, request, task_id: int):
        return get_object_or_404(self.tasks, id=task_id)


    @router.post('/{task_id}/complete', response=TaskOut)
    def complete(self, request, task_id: int):
        task = get_object_or_404(self.tasks, id=task_id)
        task.completed = True
        task.save()
        return task

```

All common initiation and permission check landed in constructor:
```Python hl_lines="5 6 7"
@router.path('/project/{project_id}/tasks')
class Tasks:

    def __init__(self, request, project_id=int):
        user_projects = request.user.project_set
        self.project = get_object_or_404(user_projects, id=project_id))
        self.tasks = self.project.task_set.all()
    
```
Which made main business operation focus only on tasks (that was exposed as `self.tasks` attribute)

you can use both `api` and `router` instances to support class paths

## Issue

The `__init__` method:

```def __init__(self, request, project_id=int):```

Python do not support `async` keyword for `__init__`, so to support async operations - we need some other method for initialization, but `__init__` sounds most logical


## Your thoughts/proposals

Please give you thoughts/likes/dislikes about this proposal in the [github issue](https://github.com/vitalik/django-ninja/issues/15)



