# Query parameters

When you declare other function parameters that are not part of the path parameters, they are automatically interpreted as "query" parameters.

```Python hl_lines="5"
{!./src/tutorial/query/code01.py!}
```

To query this operation we would use url like

```
http://localhost:8000/api/weapons?offset=0&limit=10
```
By default all GET parameters are strings, and when you annotate your function arguments with types, they are converted to that type and validated against it.

All the same process that applied for path parameters also applies for query parameters:

- Editor support (obviously)
- Data "parsing"
- Data validation
- Automatic documentation


Note: if you do not annotate your arguments - it will be treated as `str` types:

```Python hl_lines="2"
@api.get("/weapons")
def list_weapons(request, limit, offset):
    return weapons[offset : offset + limit]
```

### Defaults

As query parameters are not a fixed part of a path, they can be optional and can have default values.

In the example above they have default values of `offset=0` and `limit=10`.

So, going to the URL:
```
http://localhost:8000/api/weapons
```
would be the same as going to:
```
http://localhost:8000/api/weapons?offset=0&limit=10
```
But if you go to, for example:
```
http://localhost:8000/api/weapons?offset=20
```

The parameter values in your function will be:

 - `offset=20`: because you set it in the URL
 - `limit=10`: because that was the default value


### Required and optional parameters

You can declare required or optional GET parameters same way as you declare python function arguments:

```Python hl_lines="5"
{!./src/tutorial/query/code02.py!}
```

In this case Django Ninja will always validate that you pass `q` param in GET, and `offset` param is optional integer

### GET parameters type conversion

Let's declare multiple type arguments:
```Python hl_lines="5"
{!./src/tutorial/query/code03.py!}
```
The `str` type is passed as is

For `bool` type all of the following:s
```
http://localhost:8000/api/example?b=1
http://localhost:8000/api/example?b=True
http://localhost:8000/api/example?b=true
http://localhost:8000/api/example?b=on
http://localhost:8000/api/example?b=yes
```
or any other case variation (uppercase, first letter in uppercase, etc), your function will see the parameter `b` with a `bool` value of `True`. Otherwise as `False`.

Date can be both date string and integer (unix timestamp):

<pre style="font-size: .85em; background-color:rgb(245, 245, 245);">
http://localhost:8000/api/example?d=<strong>1577836800</strong>  # = 2020-01-01
http://localhost:8000/api/example?d=<strong>2020-01-01</strong>
</pre>


### Using Schema

You can as well use Schema to encapsulate GET parameters:

```Python hl_lines="1 2  5 6 7 8"
{!./src/tutorial/query/code010.py!}
```
