# Path parameters
You can declare path "parameters" with the same syntax used by Python format-strings (which luckily also matches the <a href="https://swagger.io/docs/specification/describing-parameters/#path-parameters" target="_blank">openapi path parameters</a>):

```Python hl_lines="1 2"
{!./src/tutorial/path/code01.py!}
```

The value of the path parameter `item_id` will be passed to your function as the argument `item_id`.

So, if you run this example and go to <a href="http://localhost:8000/api/items/foo" target="_blank">http://localhost:8000/api/items/foo</a>, you will see a response of:

```JSON
{"item_id":"foo"}
```


### Path parameters with types
You can declare the type of a path parameter in the function, using standard Python type annotations:

```Python hl_lines="2"
{!./src/tutorial/path/code02.py!}
```

In this case, `item_id` is declared to be an **`int`**. This will give you editor and linter support for error checks, completion, etc.

If you run this in your browser with <a href="http://localhost:8000/api/items/3" target="_blank">http://localhost:8000/api/items/3</a>, you will see a response of:
```JSON
{"item_id":3}
```

!!! tip
    Notice that the value your function received (and returned) is **3**, as a Python `int`, not a string `"3"`.
    So, with just that type declaration, Django Ninja gives you automatic request "parsing" and validation.




### Data validation
On the other hand if you go to the browser at <a href="http://localhost:8000/api/items/foo" target="_blank">http://localhost:8000/api/items/foo</a> <small>*(`"foo"` is not int)*</small> you will see a HTTP error of:

```JSON hl_lines="8"
{
    "detail": [
        {
            "loc": [
                "path",
                "item_id"
            ],
            "msg": "value is not a valid integer",
            "type": "type_error.integer"
        }
    ]
}
```


### Multiple parameters

You can pass as many variables as you want variables into path, just keep in mind to have unique names and not forget to use same names in function arguments.

```Python
@api.get("/events/{year}/{month}/{day}")
def events(request, year: int, month: int, day: int):
    return {"date": [year, month, day]}
```


### Using Schema

You can as well use Schema to encapsulate path parameters that depend on each other (and validate them as a group)


```Python hl_lines="1 2  5 6 7 8 9 10 11 15"
{!./src/tutorial/path/code010.py!}
```

!!! note
    Notice that here we used a `Path` source hint to let Django Ninja know that this schema will be applied to path parameters.

### Documentation
And when you open your browser at <a href="http://localhost:8000/api/docs" target="_blank">http://localhost:8000/api/docs</a>, you will see an automatic, interactive, API documentation like:
![Django Ninja Swagger](../img/tutorial-path-swagger.png)

