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
    Webhooks are **documentation only**. Django Ninja does not send them for you. See [Sending webhooks](#sending-webhooks) below.

The decorator returns the class unchanged, so you can keep using `OrderPaid` as a regular Schema.

The name is optional - if you skip it, the class name is used:

```python
@api.webhook
class OrderPaid(Schema):  # webhook name: "OrderPaid"
    id: int
```

## Options

```python
@api.webhook(
    "order.refunded",             # optional, defaults to the class name
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

## Sending webhooks

Django Ninja **intentionally** does not send webhooks (at least for now). Delivering webhooks in production takes decisions that belong to your project:

- where subscriptions are stored (who wants which event, at what URL)
- how payloads are signed, so receivers can verify them
- retries, backoff, timeouts, and what to do with endpoints that keep failing
- which task queue runs the deliveries

Rather than picking one answer for everyone, Django Ninja documents the contract (the payload Schema) and leaves delivery to you. Below is one way to do it with the [Django tasks framework](https://docs.djangoproject.com/en/stable/topics/tasks/) (built into Django 6.0+; on older versions use the [django-tasks](https://pypi.org/project/django-tasks/) package, which has the same API).

**1. A task that delivers one webhook:**

```python
# orders/tasks.py
import hashlib
import hmac
import json

import requests
from django.tasks import task


@task
def deliver_webhook(url: str, secret: str, event: str, payload: dict) -> None:
    body = json.dumps(payload).encode()
    signature = hmac.new(secret.encode(), body, hashlib.sha256).hexdigest()
    response = requests.post(
        url,
        data=body,
        headers={
            "Content-Type": "application/json",
            "X-Webhook-Event": event,
            "X-Webhook-Signature": f"sha256={signature}",
        },
        timeout=10,
    )
    response.raise_for_status()  # marks the task as failed
```

Task arguments must be JSON-serializable, so the payload is passed as a dict, not as a Schema instance.

**2. A helper that enqueues it for every subscriber:**

```python
# orders/webhooks.py
from django.db import transaction

from ninja import Schema

from .models import WebhookSubscription  # your model: url, secret, event
from .tasks import deliver_webhook


def send_webhook(event: str, payload: Schema) -> None:
    data = payload.model_dump(mode="json")  # Decimal, datetime, ... -> JSON types

    def enqueue():
        for sub in WebhookSubscription.objects.filter(event=event):
            deliver_webhook.enqueue(sub.url, sub.secret, event, data)

    # don't notify anyone about data that might still be rolled back
    transaction.on_commit(enqueue)
```

**3. Send it where the event happens:**

```python
@api.webhook("order.paid")
class OrderPaid(Schema):
    id: int
    total: Decimal


@api.post("/orders/{order_id}/pay")
def pay(request, order_id: int):
    order = get_object_or_404(Order, id=order_id)
    order.mark_paid()
    send_webhook("order.paid", OrderPaid(id=order.id, total=order.total))
    return {"success": True}
```

Using the same `OrderPaid` Schema for the documentation and for building the payload keeps them in sync: whatever you send is exactly what your OpenAPI schema describes.

!!! warning
    Django's default task backend (`ImmediateBackend`) runs tasks right away, inside the request. That's fine for development and tests. In production, configure a backend with a real worker in the `TASKS` setting (for example the database backend from `django-tasks`), so slow or failing receivers don't slow down your API. Retries depend on the backend you choose.
