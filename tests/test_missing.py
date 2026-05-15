from ninja import Schema

try:
    from pydantic.experimental.missing_sentinel import MISSING
except ImportError:
    MISSING = None


class Contact(Schema):
    name: str
    number: int | MISSING = MISSING
    address: str | None = None


def test_missing_serialization():
    contact = Contact(name="Sam")
    if MISSING is None:
        assert contact.model_dump() == {"name": "Sam", "address": None, "number": None}
    else:
        assert contact.model_dump() == {"name": "Sam", "address": None}


def test_missing_json_schema():
    schema = Contact.json_schema()
    output = {
        "properties": {
            "name": {
                "title": "Name",
                "type": "string",
            },
            "number": {
                "title": "Number",
                "type": "integer",
            },
            "address": {
                "anyOf": [
                    {
                        "type": "string",
                    },
                    {
                        "type": "null",
                    },
                ],
                "title": "Address",
            },
        },
        "required": ["name"],
        "title": "Contact",
        "type": "object",
    }
    if MISSING is None:
        output["properties"]["number"] = {
            "anyOf": [{"type": "integer"}, {"type": "null"}],
            "title": "Number",
        }
        assert schema == output
    else:
        assert schema == output
