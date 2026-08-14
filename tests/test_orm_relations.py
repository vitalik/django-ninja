from django.db import models

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


def test_foreignobject_reverse_relation():
    # A plain ForeignObject (unlike ForeignKey) uses the bare
    # ForeignObjectRel as its rel_class, not ManyToOneRel. Building a
    # schema for the related-to model must still skip that reverse
    # relation instead of trying to read .help_text off it.
    # https://github.com/vitalik/django-ninja/issues/1530
    from someapp.models import ForeignObjectTarget

    schema = create_schema(ForeignObjectTarget)

    assert "sources" not in schema.model_fields
