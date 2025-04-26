def test_inheritance_example():
    """django-pydantic.md"""
    from django.db import models
    from pydantic import model_serializer

    from ninja import ModelSchema, Schema

    # <proj_schemas.py>
    def _my_magic_serializer(self, handler):
        dump = handler(self)
        dump["magic"] = "shazam"
        return dump

    class ProjSchema(Schema):
        # pydantic configuration
        _my_magic_serilizer = model_serializer(mode="wrap")(_my_magic_serializer)
        model_config = {"arbitrary_types_allowed": True}

    class ProjModelSchema(ProjSchema, ModelSchema):
        # ModelSchema specific configuration
        pass

    class ProjMeta:
        # ModelSchema Meta defaults
        primary_key_optional = False

    # </proj_schemas.py>

    # <models.py>
    class Item(models.Model):
        name = models.CharField(max_length=64)
        type = models.CharField(max_length=64)
        desc = models.CharField(max_length=255, blank=True, null=True)

        class Meta:
            app_label = "test"

    class Event(models.Model):
        name = models.CharField(max_length=64)
        action = models.CharField(max_length=64)

        class Meta:
            app_label = "test"

    # </models.py>

    # <schemas.py>
    # All schemas will be using the configuration defined in parent Schemas
    class ItemSlimGetSchema(ProjModelSchema):
        class Meta(ProjMeta):
            model = Item
            fields = ["id", "name"]

    class ItemGetSchema(ItemSlimGetSchema):
        class Meta(ItemSlimGetSchema.Meta):
            # inherits model, and the parents fields are already set in __annotations__
            fields = ["type", "desc"]

    class EventGetSchema(ProjModelSchema):
        class Meta(ProjMeta):
            model = Event
            fields = ["id", "name"]

    class ItemSummarySchema(ProjSchema):
        model_config = {
            # extra pydantic config
            "title": "Item Summary"
        }
        name: str
        event: EventGetSchema
        item: ItemGetSchema

    # </schemas.py>
    item = Item(id=1, name="test", type="amazing", desc=None)
    event = Event(id=1, name="event", action="testing")
    summary = ItemSummarySchema(name="summary", event=event, item=item)

    assert summary.json_schema() == {
        "$defs": {
            "EventGetSchema": {
                "properties": {
                    "id": {
                        "title": "ID",
                        "type": "integer",
                    },
                    "name": {
                        "maxLength": 64,
                        "title": "Name",
                        "type": "string",
                    },
                },
                "required": [
                    "id",
                    "name",
                ],
                "title": "EventGetSchema",
                "type": "object",
            },
            "ItemGetSchema": {
                "properties": {
                    "id": {
                        "title": "ID",
                        "type": "integer",
                    },
                    "name": {
                        "maxLength": 64,
                        "title": "Name",
                        "type": "string",
                    },
                    "type": {
                        "maxLength": 64,
                        "title": "Type",
                        "type": "string",
                    },
                    "desc": {
                        "anyOf": [
                            {
                                "maxLength": 255,
                                "type": "string",
                            },
                            {
                                "type": "null",
                            },
                        ],
                        "title": "Desc",
                    },
                },
                "required": [
                    "id",
                    "name",
                    "type",
                ],
                "title": "ItemGetSchema",
                "type": "object",
            },
        },
        "properties": {
            "name": {
                "title": "Name",
                "type": "string",
            },
            "event": {
                "$ref": "#/$defs/EventGetSchema",
            },
            "item": {
                "$ref": "#/$defs/ItemGetSchema",
            },
        },
        "required": [
            "name",
            "event",
            "item",
        ],
        "title": "Item Summary",
        "type": "object",
    }
