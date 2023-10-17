# Query parameters

When you declare other function parameters that are not part of the path parameters, they are automatically interpreted as "query" parameters.

```python hl_lines="5"
{!./src/tutorial/query/code01.py!}
```

To query this operation, you use a URL like:

```
http://localhost:8000/api/weapons?offset=0&limit=10
```
By default, all GET parameters are strings, and when you annotate your function arguments with types, they are converted to that type and validated against it.

The same benefits that apply to path parameters also apply to query parameters:

- Editor support (obviously)
- Data "parsing"
- Data validation
- Automatic documentation


!!! Note
    if you do not annotate your arguments, they will be treated as `str` types

```python hl_lines="2"
@api.get("/weapons")
def list_weapons(request, limit, offset):
    # type(limit) == str
    # type(offset) == str
```

### Defaults

As query parameters are not a fixed part of a path, they are optional and can have default values:

```python hl_lines="2"
@api.get("/weapons")
def list_weapons(request, limit: int = 10, offset: int = 0):
    return weapons[offset : offset + limit]
```

In the example above we set default values of `offset=0` and `limit=10`.

So, going to the URL:
```
http://localhost:8000/api/weapons
```
would be the same as going to:
```
http://localhost:8000/api/weapons?offset=0&limit=10
```
If you go to, for example:
```
http://localhost:8000/api/weapons?offset=20
```

the parameter values in your function will be:

 - `offset=20`  (because you set it in the URL)
 - `limit=10`  (because that was the default value)


### Required and optional parameters

You can declare required or optional GET parameters in the same way as declaring Python function arguments:

```python hl_lines="5"
{!./src/tutorial/query/code02.py!}
```

In this case, **Django Ninja** will always validate that you pass the `q` param in the GET, and the `offset` param is an optional integer.

### GET parameters type conversion

Let's declare multiple type arguments:
```python hl_lines="5"
{!./src/tutorial/query/code03.py!}
```
The `str` type is passed as is.

For the `bool` type, all the following:
```
http://localhost:8000/api/example?b=1
http://localhost:8000/api/example?b=True
http://localhost:8000/api/example?b=true
http://localhost:8000/api/example?b=on
http://localhost:8000/api/example?b=yes
```
or any other case variation (uppercase, first letter in uppercase, etc.), your function will see
the parameter `b` with a `bool` value of `True`, otherwise as `False`.

Date can be both date string and integer (unix timestamp):

<pre style="font-size: .85em; background-color:rgb(245, 245, 245);">
http://localhost:8000/api/example?d=<strong>1577836800</strong>  # same as 2020-01-01
http://localhost:8000/api/example?d=<strong>2020-01-01</strong>
</pre>


### Using Schema

You can also use Schema to encapsulate GET parameters:

```python hl_lines="1 2  5 6 7 8"
{!./src/tutorial/query/code010.py!}
```

For more complex filtering scenarios please refer to [filtering](./filtering.md).
