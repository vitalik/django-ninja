# CRUD example


**CRUD**  - **C**reate, **R**etrieve, **U**pdate, **D**elete are the four basic functions of persistent storage.

This example will show you how to implement these functions with **Django Ninja**.

Let's say you have the following Django models that you need to perform these operations on:


```python

class Department(models.Model):
    title = models.CharField(max_length=100)

class Employee(models.Model):
    first_name = models.CharField(max_length=100)
    last_name = models.CharField(max_length=100)
    department = models.ForeignKey(Department, on_delete=models.CASCADE)
    birthdate = models.DateField(null=True, blank=True)
    cv = models.FileField(null=True, blank=True)
```

Now let's create CRUD operations for the Employee model.

## Create

To create an employee lets define an INPUT schema:

```python
from datetime import date
from ninja import Schema

class EmployeeIn(Schema):
    first_name: str
    last_name: str
    department_id: int = None
    birthdate: date = None

```

This schema will be our input payload:

```python hl_lines="2"
@api.post("/employees")
def create_employee(request, payload: EmployeeIn):
    employee = Employee.objects.create(**payload.dict())
    return {"id": employee.id}
```

!!! tip
    `Schema` objects have `.dict()` method with all the schema attributes represented as a dict.

    You can pass it as `**kwargs` to the Django model's `create` method (or model `__init__`).

See the recipe below for handling the file upload (when using Django models):

```python hl_lines="2"
from ninja import UploadedFile, File

@api.post("/employees")
def create_employee(request, payload: EmployeeIn, cv: File[UploadedFile]):
    payload_dict = payload.dict()
    employee = Employee(**payload_dict)
    employee.cv.save(cv.name, cv) # will save model instance as well
    return {"id": employee.id}
```

If you just need to handle a file upload:

```python hl_lines="2"
from django.core.files.storage import FileSystemStorage
from ninja import UploadedFile, File

STORAGE = FileSystemStorage()

@api.post("/upload")
def create_upload(request, cv: File[UploadedFile]):
    filename = STORAGE.save(cv.name, cv)
    # Handle things further
```

## Retrieve

### Single object

Now to get employee we will define a schema that will describe what our responses will look like. Here we will basically use the same schema as `EmployeeIn`, but will add an extra attribute `id`:


```python hl_lines="2"
class EmployeeOut(Schema):
    id: int
    first_name: str
    last_name: str
    department_id: int = None
    birthdate: date = None
```

!!! note
    Defining response schemas are not really required, but when you do define it you will get results validation, documentation and automatic ORM objects to JSON conversions.

We will use this schema as the `response` type for our `GET` employee view:


```python hl_lines="1"
@api.get("/employees/{employee_id}", response=EmployeeOut)
def get_employee(request, employee_id: int):
    employee = get_object_or_404(Employee, id=employee_id)
    return employee
```

Notice that we simply returned an employee ORM object, without a need to convert it to a dict. The `response` schema does automatic result validation and conversion to JSON:
```python hl_lines="4"
@api.get("/employees/{employee_id}", response=EmployeeOut)
def get_employee(request, employee_id: int):
    employee = get_object_or_404(Employee, id=employee_id)
    return employee
```

### List of objects

To output a list of employees, we can reuse the same `EmployeeOut` schema. We will just set the `response` schema to a *List* of `EmployeeOut`.
```python hl_lines="3"
from typing import List

@api.get("/employees", response=List[EmployeeOut])
def list_employees(request):
    qs = Employee.objects.all()
    return qs
```

Another cool trick - notice we just returned a Django ORM queryset:

```python hl_lines="4"
@api.get("/employees", response=List[EmployeeOut])
def list_employees(request):
    qs = Employee.objects.all()
    return qs
```
It automatically gets evaluated, validated and converted to a JSON list!



## Update

Update is pretty trivial. We just use the `PUT` method and also pass `employee_id`:

```python hl_lines="1"
@api.put("/employees/{employee_id}")
def update_employee(request, employee_id: int, payload: EmployeeIn):
    employee = get_object_or_404(Employee, id=employee_id)
    for attr, value in payload.dict().items():
        setattr(employee, attr, value)
    employee.save()
    return {"success": True}
```

**Note**

Here we used the `payload.dict` method to set all object attributes:

`for attr, value in payload.dict().items()`

You can also do this more explicit:

```python
employee.first_name = payload.first_name
employee.last_name = payload.last_name
employee.department_id = payload.department_id
employee.birthdate = payload.birthdate
```

**Partial updates**

To allow the user to make partial updates, use `payload.dict(exclude_unset=True).items()`. This ensures that only the specified fields get updated.

**Enforcing strict field validation**

By default, any provided fields that don't exist in the schema will be silently ignored. To raise an error for these invalid fields, you can set `extra = "forbid"` in the schema's Config class. For example:

```python hl_lines="4 5"
class EmployeeIn(Schema):
    # your fields here...

    class Config:
        extra = "forbid"
```

## Delete

Delete is also pretty simple. We just get employee by `id` and delete it from the DB:


```python hl_lines="1 2 4"
@api.delete("/employees/{employee_id}")
def delete_employee(request, employee_id: int):
    employee = get_object_or_404(Employee, id=employee_id)
    employee.delete()
    return {"success": True}
```

## Final code

Here's a full CRUD example:


```python
from datetime import date
from typing import List
from ninja import NinjaAPI, Schema
from django.shortcuts import get_object_or_404
from employees.models import Employee


api = NinjaAPI()


class EmployeeIn(Schema):
    first_name: str
    last_name: str
    department_id: int = None
    birthdate: date = None


class EmployeeOut(Schema):
    id: int
    first_name: str
    last_name: str
    department_id: int = None
    birthdate: date = None


@api.post("/employees")
def create_employee(request, payload: EmployeeIn):
    employee = Employee.objects.create(**payload.dict())
    return {"id": employee.id}


@api.get("/employees/{employee_id}", response=EmployeeOut)
def get_employee(request, employee_id: int):
    employee = get_object_or_404(Employee, id=employee_id)
    return employee


@api.get("/employees", response=List[EmployeeOut])
def list_employees(request):
    qs = Employee.objects.all()
    return qs


@api.put("/employees/{employee_id}")
def update_employee(request, employee_id: int, payload: EmployeeIn):
    employee = get_object_or_404(Employee, id=employee_id)
    for attr, value in payload.dict().items():
        setattr(employee, attr, value)
    employee.save()
    return {"success": True}


@api.delete("/employees/{employee_id}")
def delete_employee(request, employee_id: int):
    employee = get_object_or_404(Employee, id=employee_id)
    employee.delete()
    return {"success": True}
```
