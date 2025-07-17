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


@router.get("/test-headers")
def get_headers(request):
    return dict(request.headers)


@router.get("/test-cookies")
def get_cookies(request):
    return dict(request.COOKIES)


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


class ClientTestSchema(Schema):
    time: datetime


def test_schema_as_data():
    schema_instance = ClientTestSchema(time=timezone.now().replace(microsecond=0))

    with mock.patch.object(client, "_call") as call:
        client.post("/test", json=schema_instance)
        request = call.call_args[0][1]
        assert (
            ClientTestSchema.model_validate_json(request.body).model_dump_json()
            == schema_instance.model_dump_json()
        )


def test_json_as_body():
    schema_instance = ClientTestSchema(time=timezone.now().replace(microsecond=0))

    with mock.patch.object(client, "_call") as call:
        client.post(
            "/test",
            data=schema_instance.model_dump_json(),
            content_type="application/json",
        )
        request = call.call_args[0][1]
        assert (
            ClientTestSchema.model_validate_json(request.body).model_dump_json()
            == schema_instance.model_dump_json()
        )


headered_client = TestClient(router, headers={"A": "a", "B": "b"})


def test_client_request_only_header():
    r = client.get("/test-headers", headers={"A": "na"})
    assert r.json() == {"A": "na"}


def test_headered_client_request_with_default_headers():
    r = headered_client.get("/test-headers")
    assert r.json() == {"A": "a", "B": "b"}


def test_headered_client_request_with_overwritten_and_additional_headers():
    r = headered_client.get("/test-headers", headers={"A": "na", "C": "nc"})
    assert r.json() == {"A": "na", "B": "b", "C": "nc"}


cookied_client = TestClient(router, COOKIES={"A": "a", "B": "b"})


def test_client_request_only_cookies():
    r = client.get("/test-cookies", COOKIES={"A": "na"})
    assert r.json() == {"A": "na"}


def test_headered_client_request_with_default_cookies():
    r = cookied_client.get("/test-cookies")
    assert r.json() == {"A": "a", "B": "b"}


def test_headered_client_request_with_overwritten_and_additional_cookies():
    r = cookied_client.get("/test-cookies", COOKIES={"A": "na", "C": "nc"})
    assert r.json() == {"A": "na", "B": "b", "C": "nc"}
