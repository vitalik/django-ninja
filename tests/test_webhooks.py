from datetime import datetime
from decimal import Decimal
from typing import List

import pytest
from pydantic import BaseModel

from ninja import NinjaAPI, Router, Schema
from ninja.errors import ConfigError
from ninja.webhooks import Webhook, get_webhooks


class Item(Schema):
    sku: str
    quantity: int


def test_webhook_in_openapi_schema():
    api = NinjaAPI()

    @api.webhook("order.paid")
    class OrderPaid(Schema):
        id: int
        total: Decimal

    schema = api.get_openapi_schema(path_prefix="")

    assert schema["webhooks"] == {
        "order.paid": {
            "post": {
                "summary": "Order Paid",
                "requestBody": {
                    "content": {
                        "application/json": {
                            "schema": {"$ref": "#/components/schemas/OrderPaid"}
                        }
                    },
                    "required": True,
                },
                "responses": {200: {"description": "OK"}},
            }
        }
    }
    order_paid = schema["components"]["schemas"]["OrderPaid"]
    assert order_paid["type"] == "object"
    assert order_paid["properties"]["id"] == {"title": "Id", "type": "integer"}
    assert "total" in order_paid["properties"]
    assert order_paid["required"] == ["id", "total"]


def test_decorator_returns_class_unchanged():
    api = NinjaAPI()

    class OrderPaid(Schema):
        id: int

    assert api.webhook("order.paid")(OrderPaid) is OrderPaid
    assert OrderPaid(id=1).model_dump() == {"id": 1}


def test_name_defaults_to_class_name():
    api = NinjaAPI()
    router = Router()

    @api.webhook
    class OrderPaid(Schema):
        id: int

    @api.webhook()
    class OrderShipped(Schema):
        id: int

    @router.webhook
    class OrderRefunded(Schema):
        id: int

    @router.webhook(summary="Cancelled")
    class OrderCancelled(Schema):
        id: int

    api.add_router("/orders", router)

    assert OrderPaid(id=1).id == 1  # bare decorator returns the class
    webhooks = api.get_openapi_schema(path_prefix="")["webhooks"]
    assert list(webhooks) == [
        "OrderPaid",
        "OrderShipped",
        "OrderRefunded",
        "OrderCancelled",
    ]
    assert webhooks["OrderPaid"]["post"]["summary"] == "Order Paid"
    assert webhooks["OrderCancelled"]["post"]["summary"] == "Cancelled"


def test_get_webhooks():
    api = NinjaAPI()

    @api.webhook("order.paid")
    class OrderPaid(Schema):
        id: int

    webhooks = get_webhooks(api)
    assert [(w.name, w.schema, w.method) for w in webhooks] == [
        ("order.paid", OrderPaid, "post")
    ]


def test_no_webhooks_no_section():
    api = NinjaAPI()
    assert "webhooks" not in api.get_openapi_schema(path_prefix="")


def test_webhook_options():
    api = NinjaAPI()

    @api.webhook(
        "order.refunded",
        method="PUT",
        summary="Refund",
        description="Sent when an order is refunded",
        tags=["orders"],
        operation_id="order_refunded",
        deprecated=True,
        openapi_extra={
            "responses": {410: {"description": "Unsubscribe"}},
            "x-custom": 1,
        },
    )
    class OrderRefunded(Schema):
        id: int

    details = api.get_openapi_schema(path_prefix="")["webhooks"]["order.refunded"][
        "put"
    ]
    assert details["summary"] == "Refund"
    assert details["description"] == "Sent when an order is refunded"
    assert details["tags"] == ["orders"]
    assert details["operationId"] == "order_refunded"
    assert details["deprecated"] is True
    assert details["responses"] == {
        200: {"description": "OK"},
        410: {"description": "Unsubscribe"},
    }
    assert details["x-custom"] == 1


def test_include_in_schema_false():
    api = NinjaAPI()

    @api.webhook("hidden", include_in_schema=False)
    class Hidden(Schema):
        id: int

    @api.webhook("visible")
    class Visible(Schema):
        id: int

    schema = api.get_openapi_schema(path_prefix="")
    assert list(schema["webhooks"]) == ["visible"]
    assert "Hidden" not in schema["components"]["schemas"]


def test_nested_schemas_go_to_components():
    api = NinjaAPI()

    @api.webhook("order.created")
    class OrderCreated(Schema):
        items: List[Item]
        created: datetime

    schema = api.get_openapi_schema(path_prefix="")
    components = schema["components"]["schemas"]
    assert components["OrderCreated"]["properties"]["items"] == {
        "title": "Items",
        "type": "array",
        "items": {"$ref": "#/components/schemas/Item"},
    }
    assert components["Item"]["properties"] == {
        "sku": {"title": "Sku", "type": "string"},
        "quantity": {"title": "Quantity", "type": "integer"},
    }


def test_payload_uses_aliases():
    api = NinjaAPI()

    class AliasedPayload(BaseModel):
        user_id: int

        model_config = {"alias_generator": lambda n: n.upper()}

    api.webhook("aliased")(AliasedPayload)

    components = api.get_openapi_schema(path_prefix="")["components"]["schemas"]
    assert list(components["AliasedPayload"]["properties"]) == ["USER_ID"]


def test_plain_pydantic_model_is_accepted():
    api = NinjaAPI()

    @api.webhook("ping")
    class Ping(BaseModel):
        message: str

    ref = api.get_openapi_schema(path_prefix="")["webhooks"]["ping"]["post"][
        "requestBody"
    ]
    assert ref["content"]["application/json"]["schema"] == {
        "$ref": "#/components/schemas/Ping"
    }


def test_non_schema_raises():
    api = NinjaAPI()

    with pytest.raises(ConfigError, match="must be a Schema"):

        @api.webhook("bad")
        def handler(payload: Item):  # pragma: no cover
            pass

    with pytest.raises(ConfigError, match="must be a Schema"):
        api.webhook("bad")(dict)  # type: ignore


def test_duplicate_name_raises():
    api = NinjaAPI()

    @api.webhook("order.paid")
    class OrderPaid(Schema):
        id: int

    with pytest.raises(ConfigError, match='"order.paid" is already registered'):

        @api.webhook("order.paid")
        class OrderPaid2(Schema):
            id: int


def test_router_webhooks():
    api = NinjaAPI()
    orders = Router(tags=["orders"])
    nested = Router()
    orders.add_router("/nested", nested)

    @orders.webhook("order.paid")
    class OrderPaid(Schema):
        id: int

    @orders.webhook("order.shipped", tags=["shipping"])
    class OrderShipped(Schema):
        id: int

    @nested.webhook("order.nested")
    class OrderNested(Schema):
        id: int

    @api.webhook("api.level")
    class ApiLevel(Schema):
        id: int

    api.add_router("/orders", orders)

    webhooks = api.get_openapi_schema(path_prefix="")["webhooks"]
    assert set(webhooks) == {"api.level", "order.paid", "order.shipped", "order.nested"}
    assert "tags" not in webhooks["api.level"]["post"]
    # router tags are inherited, like for operations
    assert webhooks["order.paid"]["post"]["tags"] == ["orders"]
    assert webhooks["order.nested"]["post"]["tags"] == ["orders"]
    # explicit tags win
    assert webhooks["order.shipped"]["post"]["tags"] == ["shipping"]
    # template is not mutated by tag inheritance
    assert orders.webhooks["order.paid"].tags is None


def test_router_tags_from_add_router():
    api = NinjaAPI()
    router = Router()

    @router.webhook("order.paid")
    class OrderPaid(Schema):
        id: int

    api.add_router("/orders", router, tags=["mounted"])

    webhooks = api.get_openapi_schema(path_prefix="")["webhooks"]
    assert webhooks["order.paid"]["post"]["tags"] == ["mounted"]


def test_router_mounted_twice_lists_webhook_once():
    api = NinjaAPI()
    router = Router()

    @router.webhook("order.paid")
    class OrderPaid(Schema):
        id: int

    api.add_router("/v1", router, url_name_prefix="v1")
    api.add_router("/v2", router, url_name_prefix="v2")

    assert list(api.get_openapi_schema(path_prefix="")["webhooks"]) == ["order.paid"]


def test_router_shared_between_apis():
    router = Router()

    @router.webhook("order.paid")
    class OrderPaid(Schema):
        id: int

    for urls_namespace in ("one", "two"):
        api = NinjaAPI(urls_namespace=urls_namespace)
        api.add_router("/orders", router)
        assert list(api.get_openapi_schema(path_prefix="")["webhooks"]) == [
            "order.paid"
        ]


def test_same_name_in_two_routers_raises():
    api = NinjaAPI()
    r1, r2 = Router(), Router()

    @r1.webhook("order.paid")
    class OrderPaid1(Schema):
        id: int

    @r2.webhook("order.paid")
    class OrderPaid2(Schema):
        id: int

    api.add_router("/r1", r1)
    api.add_router("/r2", r2)

    with pytest.raises(ConfigError, match="registered more than once"):
        api.get_openapi_schema(path_prefix="")


def test_webhook_can_be_added_after_urls():
    api = NinjaAPI(urls_namespace="webhooks-after-urls")
    api.urls  # noqa: B018 - freezes routers

    @api.webhook("late")
    class Late(Schema):
        id: int

    assert "late" in api.get_openapi_schema(path_prefix="")["webhooks"]


def test_merges_with_openapi_extra_webhooks():
    manual = {"post": {"summary": "Manual", "responses": {}}}
    api = NinjaAPI(openapi_extra={"webhooks": {"manual": manual}})

    @api.webhook("order.paid")
    class OrderPaid(Schema):
        id: int

    webhooks = api.get_openapi_schema(path_prefix="")["webhooks"]
    assert webhooks["manual"] == manual
    assert "order.paid" in webhooks


def test_openapi_extra_webhooks_kept_without_registered_webhooks():
    manual = {"post": {"summary": "Manual", "responses": {}}}
    api = NinjaAPI(openapi_extra={"webhooks": {"manual": manual}})
    assert api.get_openapi_schema(path_prefix="")["webhooks"] == {"manual": manual}


@pytest.mark.parametrize(
    "class_name,summary",
    [
        ("OrderPaid", "Order Paid"),
        ("Ping", "Ping"),
        ("HTTPEvent", "HTTP Event"),
        ("UserV2Created", "User V2 Created"),
    ],
)
def test_default_summary(class_name, summary):
    schema = type(class_name, (Schema,), {"__annotations__": {"id": int}})
    assert Webhook(schema).summary == summary
