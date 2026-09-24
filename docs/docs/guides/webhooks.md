# Webhooks

If your API sends requests to your users' servers when something happens (an order is paid, a user signs up, etc.), you can describe those requests with **webhooks**.

Decorate the Schema of the payload with `@api.webhook(...)`, passing the event name:

```python hl_lines="8"
from decimal import Decimal

from ninja import NinjaAPI, Schema

api = NinjaAPI()


@api.webhook("order.paid")
class OrderPaid(Schema):
    id: int
    total: Decimal
```

The webhook will appear in the `webhooks` section of the OpenAPI schema (OpenAPI 3.1), so it shows up in the interactive docs next to your regular operations:

```json
"webhooks": {
  "order.paid": {
    "post": {
      "summary": "Order Paid",
      "requestBody": {
        "content": {
          "application/json": {
            "schema": {"$ref": "#/components/schemas/OrderPaid"}
          }
        },
        "required": true
      },
      "responses": {"200": {"description": "OK"}}
    }
  }
}
```

!!! note
    Webhooks are **documentation only**. Django Ninja does not send them for you. Use your preferred HTTP client (or a task queue) to deliver them, for example: `requests.post(url, data=OrderPaid(id=1, total=10).model_dump_json())`

The decorator returns the class unchanged, so you can keep using `OrderPaid` as a regular Schema.

## Options

```python
@api.webhook(
    "order.refunded",
    method="POST",                # HTTP method used to deliver the webhook
    summary="Order refunded",     # defaults to the class name: "Order Refunded"
    description="Sent when an order is fully or partially refunded",
    tags=["orders"],
    operation_id="order_refunded",
    deprecated=False,
    include_in_schema=True,
    openapi_extra={"responses": {410: {"description": "Unsubscribe"}}},
)
class OrderRefunded(Schema):
    id: int
    amount: Decimal
```

Webhook names must be unique within an API.

## Webhooks in routers

Routers support webhooks too, so you can keep them next to the code of your app:

```python
# orders/api.py
from ninja import Router, Schema

router = Router(tags=["orders"])


@router.webhook("order.paid")
class OrderPaid(Schema):
    id: int
```

Once the router is added to the API (`api.add_router("/orders", router)`), its webhooks (and the webhooks of its child routers) show up in the API schema. Router tags are applied to webhooks that do not define their own `tags`, the same way they are applied to operations.
