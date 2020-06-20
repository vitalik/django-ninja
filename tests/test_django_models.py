from someapp.models import Event
from django.test import Client
from ninja import NinjaAPI
import pytest


@pytest.mark.django_db
def test_with_client(client: Client):
    assert Event.objects.count() == 0

    test_item = {"start_date": "2020-01-01", "end_date": "2020-01-02", "title": "test"}

    response = client.post("/api/events/create", **json_payload(test_item))
    assert response.status_code == 200
    assert Event.objects.count() == 1

    response = client.get("/api/events")
    assert response.status_code == 200
    assert response.json() == [test_item]

    response = client.get("/api/events/1")
    assert response.status_code == 200
    assert response.json() == test_item


def json_payload(data):
    import json

    return dict(data=json.dumps(data), content_type="application/json")
