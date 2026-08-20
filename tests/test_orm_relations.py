from django.db import models
from django.test.utils import isolate_apps

from ninja import NinjaAPI
from ninja.orm import create_schema
from ninja.testing import TestClient


def test_manytomany():
    class SomeRelated(models.Model):
        f = models.CharField()

        class Meta:
            app_label = "tests"

    class ModelWithM2M(models.Model):
        m2m = models.ManyToManyField(SomeRelated, blank=True)

        class Meta:
            app_label = "tests"

    WithM2MSchema = create_schema(ModelWithM2M, exclude=["id"])

    api = NinjaAPI()

    @api.post("/bar")
    def post_with_m2m(request, payload: WithM2MSchema):
        return payload.dict()

    client = TestClient(api)

    response = client.post("/bar", json={"m2m": [1, 2]})
    assert response.status_code == 200, str(response.json())
    assert response.json() == {"m2m": [1, 2]}

    response = client.post("/bar", json={"m2m": []})
    assert response.status_code == 200, str(response.json())
    assert response.json() == {"m2m": []}


@isolate_apps("tests")
def test_reverse_foreign_object_relation_is_skipped():
    """A ForeignObject's reverse accessor is a bare ForeignObjectRel. Building a
    schema for the referenced model must skip it like any other reverse relation
    instead of crashing on the missing ``help_text`` attribute (see #1530)."""

    class Order(models.Model):
        class Meta:
            app_label = "tests"

    class OrderDetail(models.Model):
        order_id = models.PositiveIntegerField()
        order = models.ForeignObject(
            Order,
            on_delete=models.CASCADE,
            from_fields=["order_id"],
            to_fields=["id"],
            related_name="details",
        )

        class Meta:
            app_label = "tests"

    # Order gets a reverse ForeignObjectRel "details"; schema generation must not raise.
    OrderSchema = create_schema(Order)

    # The reverse relation is skipped, so it does not appear as a schema field.
    assert "details" not in OrderSchema.model_fields
    assert "id" in OrderSchema.model_fields
