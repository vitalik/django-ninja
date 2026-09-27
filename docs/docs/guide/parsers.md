# Request Parsers

By default, Django Ninja reads the request body as JSON, and reads query
strings, form fields and file uploads through Django's own `QueryDict`. Both
paths go through a single `Parser` object attached to the API, so you can
swap in a different content type (YAML, msgpack, ...) or a faster JSON
library without touching your operations.

## Basic usage

Pass a `parser` instance when creating the API:

```python hl_lines="2 4"
from ninja import NinjaAPI
from ninja.parser import Parser

api = NinjaAPI(parser=Parser())
```

`Parser` (from `ninja.parser`) is the default — it's what you get when you
don't pass `parser` at all. It parses [`Body`](body.md) with the standard
`json` module, and reads `Query`, `Form` and `File` values straight off
Django's `QueryDict`. The parser is set once, on the `NinjaAPI` instance, and
applies to every operation registered on it — there's no per-router or
per-operation override.

## Writing a custom parser

Subclass `ninja.parser.Parser` and override one or both of:

- **`parse_body(self, request)`** — receives the `HttpRequest` and returns
  the dict-like data used to populate `Body` parameters. This is the one
  you'll override most often, to accept a body format other than JSON.
- **`parse_querydict(self, data, list_fields, request)`** — receives a
  Django `QueryDict` (`request.GET`, `request.POST` or `request.FILES`),
  the list of field names declared with a `list` type, and the request
  itself. It's used for `Query`, `Form` and `File` parameters. The default
  implementation returns each field's single value, except fields named in
  `list_fields`, for which it calls `.getlist(...)`.

You don't need to override both — a parser that only overrides `parse_body`
still gets the default `parse_querydict` behavior, and vice versa.

!!! warning
    Errors raised from `parse_body` are caught by Django Ninja and turned
    into an HTTP 400 response (`"Cannot parse request body"`, with the
    original exception message appended when `DEBUG=True`). Errors raised
    from `parse_querydict` are **not** caught the same way, so keep it
    defensive if the input can be malformed.

## Example: a YAML parser

```python hl_lines="1 3 6-8 11"
import yaml
from ninja import NinjaAPI, Schema
from ninja.parser import Parser


class MyYamlParser(Parser):
    def parse_body(self, request):
        return yaml.safe_load(request.body)


api = NinjaAPI(parser=MyYamlParser())


class Payload(Schema):
    ints: list[int]
    string: str
    f: float


@api.post("/yaml")
def create(request, payload: Payload):
    return payload.dict()
```

Sending this as the request body (with `Content-Type` set to whatever your
client uses for YAML — Django Ninja doesn't inspect it, it just hands the
raw bytes to `parse_body`):

```yaml
ints:
  - 0
  - 1
string: hello
f: 3.14
```

gives the normal JSON response you'd expect from any other operation:

```json
{
  "ints": [0, 1],
  "string": "hello",
  "f": 3.14
}
```

## Example: a faster JSON parser

Swapping in [orjson](https://github.com/ijl/orjson) (`pip install orjson`)
for the standard library's `json` is the same pattern:

```python hl_lines="1 6-8 11"
import orjson
from ninja import NinjaAPI
from ninja.parser import Parser


class ORJSONParser(Parser):
    def parse_body(self, request):
        return orjson.loads(request.body)


api = NinjaAPI(parser=ORJSONParser())
```

## Customizing query, form and file parsing

Because `Query`, `Form` and `File` parameters all go through
`parse_querydict`, overriding it changes how all three are read. For
example, the default behavior for a `list` field is repeated keys
(`?tags=a&tags=b`, see [Multiple values (lists)](query-params.md#multiple-values-lists));
a parser can instead accept a single comma-separated value:

```python hl_lines="5-13 16"
from ninja import NinjaAPI, Query
from ninja.parser import Parser


class CommaSeparatedListParser(Parser):
    def parse_querydict(self, data, list_fields, request):
        result = {}
        for key in data.keys():
            if key in list_fields:
                result[key] = data[key].split(",")
            else:
                result[key] = data[key]
        return result


api = NinjaAPI(parser=CommaSeparatedListParser())


@api.get("/tags")
def list_tags(request, tags: list[str] = Query(...)):
    return {"tags": tags}
```

`GET /api/tags?tags=red,green,blue` now gives `tags == ["red", "green",
"blue"]`. Note this replaces the repeated-key behavior everywhere `Query`,
`Form` or `File` collect a list — there's no way to opt in per-parameter,
since the parser is shared by the whole API.

!!! tip
    A custom parser only changes how *incoming* data is read. Responses are
    still serialized by the [renderer](renderers.md), which is configured
    separately.
