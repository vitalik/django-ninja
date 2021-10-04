from functools import wraps
from unittest import mock

import pytest

from ninja import Router
from ninja.testing import TestClient

router = Router()
client = TestClient(router)


def a_good_test_wrapper(f):
    """Validate that decorators using functools.wraps(), work as expected"""

    @wraps(f)
    def wrapper(*args, **kwargs):
        return f(*args, **kwargs)

    return wrapper


def a_bad_test_wrapper(f):
    """Validate that decorators failing to using functools.wraps(), fail"""

    def wrapper(*args, **kwargs):
        return f(*args, **kwargs)

    return wrapper


@router.get("/text")
@a_good_test_wrapper
def get_text(
    request,
):
    return "Hello World"


@router.get("/path/{item_id}")
@a_good_test_wrapper
def get_id(request, item_id):
    return item_id


@router.get("/query")
@a_good_test_wrapper
def get_query_type(request, query: int):
    return f"foo bar {query}"


@router.get("/path-query/{item_id}")
@a_good_test_wrapper
def get_query_id(request, item_id, query: int):
    return f"foo bar {item_id} {query}"


@router.get("/text-bad")
@a_bad_test_wrapper
def get_text_bad(request):
    return "Hello World"


with mock.patch("ninja.signature.details.warnings.warn_explicit"):

    @router.get("/path-bad/{item_id}")
    @a_bad_test_wrapper
    def get_id_bad(request, item_id):
        return item_id


@router.get("/query-bad")
@a_bad_test_wrapper
def get_query_type_bad(request, query: int):
    return f"foo bar {query}"


with mock.patch("ninja.signature.details.warnings.warn_explicit"):

    @router.get("/path-query-bad/{item_id}")
    @a_bad_test_wrapper
    def get_query_id_bad(request, item_id, query: int):
        return f"foo bar {item_id} {query}"


@pytest.mark.parametrize(
    "path,expected_status,expected_response",
    [
        ("/text", 200, "Hello World"),
        ("/path/id", 200, "id"),
        ("/query?query=1", 200, "foo bar 1"),
        ("/path-query/id?query=2", 200, "foo bar id 2"),
        ("/text-bad", 200, "Hello World"),  # no params so passes
        ("/path-bad/id", None, TypeError),
        ("/query-bad?query=1", None, TypeError),
        ("/path-query-bad/id?query=2", None, TypeError),
    ],
)
def test_get_path(path, expected_status, expected_response):
    if isinstance(expected_response, str):
        response = client.get(path)
        assert response.status_code == expected_status
        assert response.json() == expected_response
    else:
        match = r"Did you fail to use functools.wraps\(\) in a decorator\?"
        with pytest.raises(expected_response, match=match):
            client.get(path)
