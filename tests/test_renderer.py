import json
from io import StringIO
from unittest.mock import Mock

import pytest
from django.utils.encoding import force_str
from django.utils.xmlutils import SimplerXMLGenerator

from ninja import NinjaAPI
from ninja.renderers import BaseDynamicRenderer, BaseRenderer
from ninja.responses import NinjaJSONEncoder
from ninja.testing import TestClient


def _to_xml(xml, data):
    if isinstance(data, (list, tuple)):
        for item in data:
            xml.startElement("item", {})
            _to_xml(xml, item)
            xml.endElement("item")

    elif isinstance(data, dict):
        for key, value in data.items():
            xml.startElement(key, {})
            _to_xml(xml, value)
            xml.endElement(key)

    elif data is None:
        # Don't output any value
        pass

    else:
        xml.characters(force_str(data))


class XMLRenderer(BaseRenderer):
    media_type = "text/xml"

    def render(self, request, data, *, response_status):
        stream = StringIO()
        xml = SimplerXMLGenerator(stream, "utf-8")
        xml.startDocument()
        xml.startElement("data", {})
        _to_xml(xml, data)
        xml.endElement("data")
        xml.endDocument()
        return stream.getvalue()


class CSVRenderer(BaseRenderer):
    media_type = "text/csv"

    def render(self, request, data, *, response_status):
        content = [",".join(data[0].keys())]
        for item in data:
            content.append(",".join(item.values()))
        return "\n".join(content)


class DynamicRenderer(BaseDynamicRenderer):
    media_type = "application/json"
    media_types = ["application/json", "text/csv", "text/xml"]

    def render(self, request, data, *, response_status):
        accept = request.headers.get("accept", "application/json")

        if accept.startswith("text/xml"):
            return self.render_xml(data)
        elif accept.startswith("text/csv"):
            return self.render_csv(data)
        else:
            return self.render_json(data)

    def render_csv(self, data):
        content = [",".join(data[0].keys())]
        for item in data:
            content.append(",".join(item.values()))
        return "\n".join(content)

    def render_xml(self, data):
        stream = StringIO()
        xml = SimplerXMLGenerator(stream, "utf-8")
        xml.startDocument()
        xml.startElement("data", {})
        _to_xml(xml, data)
        xml.endElement("data")
        xml.endDocument()
        return stream.getvalue()

    def render_json(self, data):
        return json.dumps(data, cls=NinjaJSONEncoder)


def operation(request):
    return [
        {"name": "Jonathan", "lastname": "Doe"},
        {"name": "Sarah", "lastname": "Calvin"},
    ]


api_xml = NinjaAPI(renderer=XMLRenderer())
api_csv = NinjaAPI(renderer=CSVRenderer())
api_dynamic = NinjaAPI(renderer=DynamicRenderer())


api_xml.get("/test")(operation)
api_csv.get("/test")(operation)
api_dynamic.get("/test")(operation)


@pytest.mark.parametrize(
    "api,content_type,expected_content",
    [
        (
            api_xml,
            "text/xml; charset=utf-8",
            '<?xml version="1.0" encoding="utf-8"?>\n<data>'
            "<item><name>Jonathan</name><lastname>Doe</lastname></item>"
            "<item><name>Sarah</name><lastname>Calvin</lastname></item>"
            "</data>",
        ),
        (
            api_csv,
            "text/csv; charset=utf-8",
            "name,lastname\nJonathan,Doe\nSarah,Calvin",
        ),
    ],
)
def test_response_class(api, content_type, expected_content):
    client = TestClient(api)
    response = client.get("/test")
    assert response.status_code == 200
    assert response["Content-Type"] == content_type
    assert response.content.decode() == expected_content


@pytest.mark.parametrize(
    "accept,expected_content",
    [
        (
            "text/xml; charset=utf-8",
            '<?xml version="1.0" encoding="utf-8"?>\n<data>'
            "<item><name>Jonathan</name><lastname>Doe</lastname></item>"
            "<item><name>Sarah</name><lastname>Calvin</lastname></item>"
            "</data>",
        ),
        (
            "text/csv; charset=utf-8",
            "name,lastname\nJonathan,Doe\nSarah,Calvin",
        ),
        (
            "application/json; charset=utf-8",
            '[{"name": "Jonathan", "lastname": "Doe"}, {"name": "Sarah", "lastname": "Calvin"}]',
        ),
    ],
)
def test_dynamic_response_class(accept, expected_content):
    client = TestClient(api_dynamic)
    response = client.get("/test", headers={"Accept": accept})
    assert response.status_code == 200
    assert response["Content-Type"] == accept
    assert response.content.decode() == expected_content


@pytest.mark.parametrize("Base", [BaseRenderer, BaseDynamicRenderer])
def test_implement_render(Base):
    class FooRenderer(Base):
        pass

    renderer = FooRenderer()
    with pytest.raises(NotImplementedError):
        renderer.render(None, None, response_status=200)


@pytest.mark.parametrize(
    "accept,expected_media_type",
    [
        ("text/xml", "text/xml"),
        ("text/csv", "text/csv"),
        ("*/*", "text/xml"),
        ("blahblahblah", "text/xml"),
    ],
)
def test_get_media_type(accept, expected_media_type):
    class FooRenderer(BaseDynamicRenderer):
        media_type = "text/xml"
        media_types = ["text/xml", "text/csv"]

    request = Mock()
    request.headers = {"accept": accept}

    assert FooRenderer().get_media_type(request) == expected_media_type
