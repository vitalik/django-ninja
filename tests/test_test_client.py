from unittest import mock
import pytest

from django.http.request import HttpHeaders
from http import HTTPStatus
from ninja.testing import TestClient
from ninja import Router

router = Router()

@router.get("/request/build_absolute_uri")
def request_build_absolute_uri(request):
    return request.build_absolute_uri()


@router.get("/request/build_absolute_uri/location")
def request_build_absolute_uri_location(request):
    return request.build_absolute_uri('location')


@router.get("/test")
def simple_get(request):
    return 'test'


client = TestClient(router)


@pytest.mark.parametrize('path,expected_status,expected_response', [
    ('/request/build_absolute_uri', HTTPStatus.OK, 'http://testlocation/'),
    ('/request/build_absolute_uri/location', HTTPStatus.OK, 'http://testlocation/location'),
])
def test_sync_build_absolute_uri(path, expected_status, expected_response):
    response = client.get(path)

    assert response.status_code == expected_status
    assert response.json() == expected_response


@pytest.mark.parametrize('version, has_headers', [
    ((2, 0), False),
    ((2, 1), False),
    ((2, 2), True),
    ((3, 0), True),
])
def test_django_2_2_plus_headers(version, has_headers):
    with mock.patch('ninja.testing.client.django', VERSION=version):
        with mock.patch.object(client, '_call') as call:
            client.get('/test')
            request = call.call_args[0][1]
            assert isinstance(request.headers, HttpHeaders) == has_headers
