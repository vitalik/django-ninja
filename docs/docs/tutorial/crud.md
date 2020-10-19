# CRUD example


**CRUD**  - **C**reate, **R**etrieve, **U**pdate, **D**elete are the four basic functions of persistent storage.

This example will show you how to implement these functions with **Django Ninja**

Let's say you have the following django models that you need to perform these operations with:


```Python

class Department(models.Model):
    title = models.CharField(max_length=100)

class Employee(models.Model):
    first_name = models.CharField(max_length=100)
    last_name = models.CharField(max_length=100)
    department = models.ForeignKey(Department)
    birthdate = models.DateField(null=True, blank=True)
```

Now let's create CRUD operations for Employee model

## Create

To create an employee lets define a INPUT schema:

```Python
from datetime import date
from ninja import Schema

class EmployeeIn(Schema):
    first_name: str
    last_name: str
    department_id: int = None
    birthdate: date = None

```

This schema will be our input payload:

```Python hl_lines="2"
@api.post("/employees")
def create_employee(request, payload: EmployeeIn):
    employee = Employee.objects.create(**payload.dict())
    return {"id": employee.id}

```

!!! tip
    `Schema` objects have `.dict()` attribute with all the schema attributes represented as dict

    You can pass it as `**kwargs` to django model `create` meothod (or model `__init__`)

## Retrieve

### Single object

Now to get employee we will define schema that will describe how our responses will look like. Here we will basically use same schema as `EmployeeIn` but will add extra attribute `id`:


```Python hl_lines="2"
class EmployeeOut(Schema):
    id: int
    first_name: str
    last_name: str
    department_id: int = None
    birthdate: date = None
```

!!! note
    Defining response schemas are not really required. But when you do define it you will get results validation, documentation and automatic ORM objects to JSON converting.

We will use this schema as `response` type for our get employee view:


```Python hl_lines="1"
@api.get("/employees/{employee_id}", response=EmployeeOut)
def get_employee(request, employee_id: int):
    employee = get_object_or_404(Employee, id=employee_id)
    return employee
```

Notice that we simply returned employee ORM object, without a need to convert it to dict. The `response` schema does automatic result validation and converting to JSON:
```Python hl_lines="4"
@api.get("/employees/{employee_id}", response=EmployeeOut)
def get_employee(request, employee_id: int):
    employee = get_object_or_404(Employee, id=employee_id)
    return employee
```

### List of objects

To output list of employees we can reuse the same schema `EmployeeOut`. We will just set `response` schema to a *List* or `EmployeeOut`
```Python hl_lines="3"
from typing import List

@api.get("/employees", response=List[EmployeeOut])
def list_employees(request):
    qs = Employee.objects.all()
    return qs
```

Another cool trick - notice we just returned a ORM queryset:

```Python hl_lines="4"
@api.get("/employees", response=List[EmployeeOut])
def list_employees(request):
    qs = Employee.objects.all()
    return qs
```
But it automatically getting evaluated, validated and converted to JSON list



## Update

The update is pretty trivial, we just use `PUT` method and also pass employee_id:

```Python hl_lines="1"
@api.put("/employees/{employee_id}")
def update_employee(request, employee_id: int, payload: EmployeeIn):
    employee = get_object_or_404(Employee, id=employee_id)
    for attr, value in payload.dict().items():
        setattr(employee, attr, value)
    employee.save()
    return {"success": True}
```

**Note**

Here we used `payload.dict` function to set all object attribute:

`for attr, value in payload.dict().items()`

You can also do this more implicit:

```Python
employee.first_name = payload.first_name
employee.last_name = payload.last_name
employee.department_id = payload.department_id
employee.birthdate = payload.birthdate
```


## Delete

The deletion is pretty simple - we just get employee by id and delete it from DB:


```Python hl_lines="1 2 4"
@api.delete("/employees/{employee_id}")
def delete_employee(request, employee_id: int):
    employee = get_object_or_404(Employee, id=employee_id)
    employee.delete()
    return {"success": True}
```

## Final code

Here is a full CRUD code:


```Python
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
