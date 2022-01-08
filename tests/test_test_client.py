from datetime import datetime
from http import HTTPStatus
from unittest import mock

import pytest
from django.utils import timezone

from ninja import Router
from ninja.schema import Schema
from ninja.testing import TestClient

router = Router()


@router.get("/request/build_absolute_uri")
def request_build_absolute_uri(request):
    return request.build_absolute_uri()


@router.get("/request/build_absolute_uri/location")
def request_build_absolute_uri_location(request):
    return request.build_absolute_uri("location")


@router.get("/test")
def simple_get(request):
    return "test"


client = TestClient(router)


@pytest.mark.parametrize(
    "path,expected_status,expected_response",
    [
        ("/request/build_absolute_uri", HTTPStatus.OK, "http://testlocation/"),
        (
            "/request/build_absolute_uri/location",
            HTTPStatus.OK,
            "http://testlocation/location",
        ),
    ],
)
def test_sync_build_absolute_uri(path, expected_status, expected_response):
    response = client.get(path)

    assert response.status_code == expected_status
    assert response.json() == expected_response


@pytest.mark.parametrize(
    "version, has_headers",
    [
        ((2, 0), False),
        ((2, 1), False),
        ((2, 2), True),
        ((3, 0), True),
    ],
)
def test_django_2_2_plus_headers(version, has_headers):
    with mock.patch("ninja.testing.client.django", VERSION=version):
        with mock.patch.object(client, "_call") as call:
            client.get("/test")
            request = call.call_args[0][1]
            # for Django >= 2.2 we apply a HttpHeaders instance to .headers
            assert isinstance(request.headers, mock.Mock) != has_headers


class ClientTestSchema(Schema):

    time: datetime


def test_schema_as_data():
    schema_instance = ClientTestSchema(time=timezone.now().replace(microsecond=0))

    with mock.patch.object(client, "_call") as call:
        client.post("/test", json=schema_instance)
        request = call.call_args[0][1]
        assert ClientTestSchema.parse_raw(request.body).json() == schema_instance.json()


def test_json_as_body():
    schema_instance = ClientTestSchema(time=timezone.now().replace(microsecond=0))

    with mock.patch.object(client, "_call") as call:
        client.post(
            "/test", data=schema_instance.json(), content_type="application/json"
        )
        request = call.call_args[0][1]
        assert ClientTestSchema.parse_raw(request.body).json() == schema_instance.json()
