from http import HTTPStatus

import pytest

from ninja import Router
from ninja.testing import TestClient

router = Router()


@router.get("/request/build_absolute_uri")
def request_build_absolute_uri(request):
    return request.build_absolute_uri()


@router.get("/request/build_absolute_uri/location")
def request_build_absolute_uri_location(request):
    return request.build_absolute_uri("location")


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
