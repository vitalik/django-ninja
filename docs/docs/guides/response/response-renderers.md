# Response renderers

The most common response type for a REST API is usually JSON.
**Django Ninja** also has support for defining your own custom renderers, which gives you the flexibility to design your own media types.

## Create a renderer

To create your own renderer, you need to inherit `ninja.renderers.BaseRenderer` and override the `render` method. Then you can pass an instance of your class to `NinjaAPI` as the `renderer` argument:

```python hl_lines="5 8 9"
from ninja import NinjaAPI
from ninja.renderers import BaseRenderer


class MyRenderer(BaseRenderer):
    media_type = "text/plain"

    def render(self, request, data, *, response_status):
        return ... # your serialization here

api = NinjaAPI(renderer=MyRenderer())
```

The `render` method takes the following arguments:

 - request -> HttpRequest object 
 - data -> object that needs to be serialized
 - response_status as an `int` -> the HTTP status code that will be returned to the client

You need also define the `media_type` attribute on the class to set the content-type header for the response.


## ORJSON renderer example:

[orjson](https://github.com/ijl/orjson#orjson) is a fast, accurate JSON library for Python. It benchmarks as the fastest Python library for JSON and is more accurate than the standard `json` library or other third-party libraries. It also serializes dataclass, datetime, numpy, and UUID instances natively.

Here's an example renderer class that uses `orjson`:


```python hl_lines="9 10"
import orjson
from ninja import NinjaAPI
from ninja.renderers import BaseRenderer


class ORJSONRenderer(BaseRenderer):
    media_type = "application/json"

    def render(self, request, data, *, response_status):
        return orjson.dumps(data)

api = NinjaAPI(renderer=ORJSONRenderer())
```



## XML renderer example:


This is how you create a renderer that outputs all responses as XML:


```python hl_lines="8 11"
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

        elif data is None:
            # Don't output any value
            pass

        else:
            xml.characters(force_str(data))


api = NinjaAPI(renderer=XMLRenderer())
```
*(Copyright note: this code is basically copied from [DRF-xml](https://jpadilla.github.io/django-rest-framework-xml/))*
