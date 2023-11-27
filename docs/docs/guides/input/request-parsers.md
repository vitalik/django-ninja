# Request parsers

In most cases, the default content type for REST API's is JSON, but in case you need to work with
other content types (like YAML, XML, CSV) or use faster JSON parsers, **Django Ninja** provides a `parser` configuration.

```python
api = NinjaAPI(parser=MyYamlParser())
```

To create your own parser, you need to extend the `ninja.parser.Parser` class, and override the `parse_body` method.


## Example YAML Parser

Let's create our custom YAML parser:

```python hl_lines="4 8 9"
import yaml
from typing import List
from ninja import NinjaAPI
from ninja.parser import Parser


class MyYamlParser(Parser):
    def parse_body(self, request):
        return yaml.safe_load(request.body)


api = NinjaAPI(parser=MyYamlParser())


class Payload(Schema):
    ints: List[int]
    string: str
    f: float


@api.post('/yaml')
def operation(request, payload: Payload):
    return payload.dict()


```

If you now send YAML like this as the request body:

```YAML
ints:
 - 0
 - 1
string: hello
f: 3.14
```

it will be correctly parsed, and you should have JSON output like this:


```JSON
{
  "ints": [
    0,
    1
  ],
  "string": "hello",
  "f": 3.14
}
```


## Example ORJSON Parser

[orjson](https://github.com/ijl/orjson#orjson) is a fast, accurate JSON library for Python. It benchmarks as the fastest Python library for JSON and is more accurate than the standard `json` library or other third-party libraries.

```
pip install orjson
```

Parser code:

```python hl_lines="1 8 9"
import orjson
from ninja import NinjaAPI
from ninja.parser import Parser


class ORJSONParser(Parser):
    def parse_body(self, request):
        return orjson.loads(request.body)


api = NinjaAPI(parser=ORJSONParser())
```

