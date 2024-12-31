import pytest
from ninja.status import HTTPStatus

def test_http_status_enum_values():
    assert HTTPStatus.HTTP_OK.value == 200
    assert HTTPStatus.HTTP_BAD_REQUEST.value == 400
    assert HTTPStatus.HTTP_NOT_FOUND.value == 404
    assert HTTPStatus.HTTP_INTERNAL_SERVER_ERROR.value == 500

def test_http_status_enum_names():
    assert HTTPStatus.HTTP_OK.name == "HTTP_OK"
    assert HTTPStatus.HTTP_BAD_REQUEST.name == "HTTP_BAD_REQUEST"
    assert HTTPStatus.HTTP_NOT_FOUND.name == "HTTP_NOT_FOUND"
    assert HTTPStatus.HTTP_INTERNAL_SERVER_ERROR.name == "HTTP_INTERNAL_SERVER_ERROR"

def test_http_status_enum_iteration():
    status_codes = list(HTTPStatus)
    assert len(status_codes) == 73
    assert HTTPStatus.HTTP_OK in status_codes

def test_invalid_http_status():
    with pytest.raises(ValueError):
        HTTPStatus(999)
