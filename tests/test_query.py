import pytest
from main import router

from ninja.testing import TestClient

response_missing = {
    "detail": [
        {
            "type": "missing",
            "loc": ["query", "query"],
            "msg": "Field required",
        }
    ]
}

response_not_valid_int = {
    "detail": [
        {
            "type": "int_parsing",
            "loc": ["query", "query"],
            "msg": "Input should be a valid integer, unable to parse string as an integer",
        }
    ]
}

response_not_valid_int_float = {
    "detail": [
        {
            "type": "int_parsing",
            "loc": ["query", "query"],
            "msg": "Input should be a valid integer, unable to parse string as an integer",
        }
    ]
}


client = TestClient(router)


@pytest.mark.parametrize(
    "path,expected_status,expected_response",
    [
        ("/query", 422, response_missing),
        ("/query?query=baz", 200, "foo bar baz"),
        ("/query?not_declared=baz", 422, response_missing),
        ("/query/optional", 200, "foo bar"),
        ("/query/optional?query=baz", 200, "foo bar baz"),
        ("/query/optional?not_declared=baz", 200, "foo bar"),
        ("/query/int", 422, response_missing),
        ("/query/int?query=42", 200, "foo bar 42"),
        ("/query/int?query=42.5", 422, response_not_valid_int_float),
        ("/query/int?query=baz", 422, response_not_valid_int),
        ("/query/int?not_declared=baz", 422, response_missing),
        ("/query/int/optional", 200, "foo bar"),
        ("/query/int/optional?query=50", 200, "foo bar 50"),
        ("/query/int/optional?query=foo", 422, response_not_valid_int),
        ("/query/int/default", 200, "foo bar 10"),
        ("/query/int/default?query=50", 200, "foo bar 50"),
        ("/query/int/default?query=foo", 422, response_not_valid_int),
        ("/query/list?query=a&query=b&query=c", 200, "a,b,c"),
        ("/query/list-optional?query=a&query=b&query=c", 200, "a,b,c"),
        ("/query/list-optional?query=a", 200, "a"),
        ("/query/list-optional", 200, None),
        ("/query/param", 200, "foo bar"),
        ("/query/param?query=50", 200, "foo bar 50"),
        ("/query/param-required", 422, response_missing),
        ("/query/param-required?query=50", 200, "foo bar 50"),
        ("/query/param-required/int", 422, response_missing),
        ("/query/param-required/int?query=50", 200, "foo bar 50"),
        ("/query/param-required/int?query=foo", 422, response_not_valid_int),
        ("/query/aliased-name?aliased.-_~name=foo", 200, "foo bar foo"),
    ],
)
def test_get_path(path, expected_status, expected_response):
    response = client.get(path)
    resp = response.json()
    print(resp)
    assert response.status_code == expected_status
    assert resp == expected_response
