from io import StringIO

import pytest
from django.utils.encoding import force_str
from django.utils.xmlutils import SimplerXMLGenerator

from ninja import NinjaAPI
from ninja.renderers import BaseRenderer
from ninja.testing import TestClient


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


class CSVRenderer(BaseRenderer):
    media_type = "text/csv"

    def render(self, request, data, *, response_status):
        content = [",".join(data[0].keys())]
        for item in data:
            content.append(",".join(item.values()))
        return "\n".join(content)


def operation(request):
    return [
        {"name": "Jonathan", "lastname": "Doe"},
        {"name": "Sarah", "lastname": "Calvin"},
    ]


api_xml = NinjaAPI(renderer=XMLRenderer())
api_csv = NinjaAPI(renderer=CSVRenderer())


api_xml.get("/test")(operation)
api_csv.get("/test")(operation)


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


def test_implment_render():
    class FooRenderer(BaseRenderer):
        pass

    renderer = FooRenderer()
    with pytest.raises(NotImplementedError):
        renderer.render(None, None, response_status=200)
