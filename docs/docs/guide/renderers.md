# Renderers

Every response Django Ninja sends — including the ones it generates itself,
like validation errors — is turned into bytes by a single **renderer**
attached to the `NinjaAPI` instance. By default that's JSON, but you can
swap in anything else: a different JSON library, XML, CSV, or a custom
media type of your own.

## Basic usage

Pass a `renderer` instance when creating the API:

```python hl_lines="2 6 9 12"
from ninja import NinjaAPI
from ninja.renderers import BaseRenderer


class TextRenderer(BaseRenderer):
    media_type = "text/plain"

    def render(self, request, data, *, response_status):
        return str(data)


api = NinjaAPI(renderer=TextRenderer())
```

The renderer is set once, on the `NinjaAPI` instance, and applies to every
operation registered on it — there's no per-router or per-operation
override.

## Writing a custom renderer

Subclass `ninja.renderers.BaseRenderer` and define:

- **`media_type`** — the media type used for the response's `Content-Type`
  header, e.g. `"application/xml"`.
- **`charset`** — defaults to `"utf-8"`. Combined with `media_type` to build
  the full header, e.g. `application/xml; charset=utf-8`.
- **`render(self, request, data, *, response_status)`** — receives the
  `HttpRequest`, the object returned by your view (already validated and
  shaped by any `response=Schema` you declared), and the `int` HTTP status
  code. Return a `str` or `bytes` value — that's exactly what goes on the
  wire as the response body.

!!! warning
    Because Django Ninja's built-in error responses (validation errors,
    `HttpError`, 404s) are serialized through the same renderer as your own
    views, `render` needs to handle plain `dict` payloads too — not just the
    shapes your own schemas produce. The XML and CSV examples below only
    work for the data shapes they were written for; a production renderer
    should be more defensive.

## The default JSON renderer

`ninja.renderers.JSONRenderer` is what you get when you don't pass
`renderer` at all. It serializes with the standard library's `json` module
and two attributes you can override:

- **`encoder_class`** — defaults to `ninja.responses.NinjaJSONEncoder`,
  which extends Django's `DjangoJSONEncoder` (so it already handles
  `datetime`, `date`, `Decimal`, `UUID`, etc.) and additionally knows how to
  serialize Pydantic models (via `.model_dump()`), `AnyUrl`/`Url` values,
  `IPv4Address`/`IPv6Address`/`IPv4Network`/`IPv6Network`, and `Enum`
  members.
- **`json_dumps_params`** — a `dict` of extra keyword arguments passed
  straight to `json.dumps(...)`, e.g. `{"indent": 2}` or
  `{"sort_keys": True}`.

Subclassing `JSONRenderer` lets you tweak either without reimplementing
`render`:

```python hl_lines="6"
from ninja import NinjaAPI
from ninja.renderers import JSONRenderer


class PrettyJSONRenderer(JSONRenderer):
    json_dumps_params = {"indent": 2}


api = NinjaAPI(renderer=PrettyJSONRenderer())
```

## Example: a faster JSON renderer

[orjson](https://github.com/ijl/orjson) is a fast JSON library that also
serializes `dataclass`, `datetime`, `numpy` and `UUID` instances natively.
Swapping it in only takes a few lines:

```python hl_lines="1 9-10 13"
import orjson
from ninja import NinjaAPI
from ninja.renderers import BaseRenderer


class ORJSONRenderer(BaseRenderer):
    media_type = "application/json"

    def render(self, request, data, *, response_status):
        return orjson.dumps(data)


api = NinjaAPI(renderer=ORJSONRenderer())
```

!!! tip
    `orjson.dumps` returns `bytes`, not `str` — that's fine, Django's
    `HttpResponse` accepts bytes content directly.

## Example: an XML renderer

```python hl_lines="10 12 20 37"
from io import StringIO

from django.utils.encoding import force_str
from django.utils.xmlutils import SimplerXMLGenerator
from ninja import NinjaAPI
from ninja.renderers import BaseRenderer


class XMLRenderer(BaseRenderer):
    media_type = "text/xml"

    def render(self, request, data, *, response_status):
        stream = StringIO()
        xml = SimplerXMLGenerator(stream, "utf-8")
        xml.startDocument()
        xml.startElement("data", {})
        self._to_xml(xml, data)
        xml.endElement("data")
        xml.endDocument()
        return stream.getvalue()

    def _to_xml(self, xml, data):
        if isinstance(data, (list, tuple)):
            for item in data:
                xml.startElement("item", {})
                self._to_xml(xml, item)
                xml.endElement("item")
        elif isinstance(data, dict):
            for key, value in data.items():
                xml.startElement(key, {})
                self._to_xml(xml, value)
                xml.endElement(key)
        elif data is not None:
            xml.characters(force_str(data))


api = NinjaAPI(renderer=XMLRenderer())
```

This code is based on
[DRF-xml](https://github.com/jpadilla/django-rest-framework-xml).

## Example: a CSV renderer

A renderer that only needs to handle one specific, known shape — a list of
flat dicts with identical keys — can be much shorter:

```python hl_lines="4-5 7-9"
from ninja.renderers import BaseRenderer


class CSVRenderer(BaseRenderer):
    media_type = "text/csv"

    def render(self, request, data, *, response_status):
        rows = [",".join(data[0].keys())]
        rows += [",".join(map(str, item.values())) for item in data]
        return "\n".join(rows)
```

## Edge cases and tips

- A renderer instance is shared across every request; keep it stateless
  (all the built-in and example renderers above only read `data`, never
  store anything on `self`).
- `get_content_type()` on `NinjaAPI` builds the response's `Content-Type`
  header as `f"{renderer.media_type}; charset={renderer.charset}"` — the
  `; charset=...` part is always appended, so setting `charset = ""` on your
  renderer only leaves you with a trailing `charset=`, not a bare media
  type. If you need the header to be exactly `media_type` with no charset
  parameter at all, override `get_content_type()` on a `NinjaAPI` subclass.
- Renderers are orthogonal to [request parsers](parsers.md): a parser
  controls how the *incoming* request body is read, a renderer controls how
  the *outgoing* response body is written. You can mix and match freely,
  e.g. accept JSON bodies but render XML responses.
