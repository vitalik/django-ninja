import pytest
from main import router

from ninja import Router
from ninja.testing import TestClient

client = TestClient(router)


def test_text_get():
    response = client.get("/text")
    assert response.status_code == 200, response.text
    assert response.json() == "Hello World"


response_not_valid_bool = {
    "detail": [
        {
            "type": "bool_parsing",
            "loc": ["path", "item_id"],
            "msg": "Input should be a valid boolean, unable to interpret input",
        }
    ]
}

response_not_valid_int = {
    "detail": [
        {
            "type": "int_parsing",
            "loc": ["path", "item_id"],
            "msg": "Input should be a valid integer, unable to parse string as an integer",
        }
    ]
}

response_not_valid_int_float = {
    "detail": [
        {
            "type": "int_parsing",
            "loc": ["path", "item_id"],
            "msg": "Input should be a valid integer, unable to parse string as an integer",
        }
    ]
}

response_not_valid_float = {
    "detail": [
        {
            "type": "float_parsing",
            "loc": ["path", "item_id"],
            "msg": "Input should be a valid number, unable to parse string as a number",
        }
    ]
}

response_at_least_3 = {
    "detail": [
        {
            "type": "string_too_short",
            "loc": ["path", "item_id"],
            "msg": "String should have at least 3 characters",
            "ctx": {"min_length": 3},
        }
    ]
}


response_at_least_2 = {
    "detail": [
        {
            "type": "string_too_short",
            "loc": ["path", "item_id"],
            "msg": "String should have at least 2 characters",
            "ctx": {"min_length": 2},
        }
    ]
}


response_maximum_3 = {
    "detail": [
        {
            "type": "string_too_long",
            "loc": ["path", "item_id"],
            "msg": "String should have at most 3 characters",
            "ctx": {"max_length": 3},
        }
    ]
}


response_greater_than_3 = {
    "detail": [
        {
            "type": "greater_than",
            "loc": ["path", "item_id"],
            "msg": "Input should be greater than 3",
            "ctx": {"gt": 3.0},
        }
    ]
}


response_greater_than_0 = {
    "detail": [
        {
            "type": "greater_than",
            "loc": ["path", "item_id"],
            "msg": "Input should be greater than 0",
            "ctx": {"gt": 0.0},
        }
    ]
}


response_greater_than_1 = {
    "detail": [
        {
            "type": "greater_than",
            "loc": ["path", "item_id"],
            "msg": "Input should be greater than 1",
            "ctx": {"gt": 1},
        }
    ]
}


response_greater_than_equal_3 = {
    "detail": [
        {
            "type": "greater_than_equal",
            "loc": ["path", "item_id"],
            "msg": "Input should be greater than or equal to 3",
            "ctx": {"ge": 3.0},
        }
    ]
}


response_less_than_3 = {
    "detail": [
        {
            "type": "less_than",
            "loc": ["path", "item_id"],
            "msg": "Input should be less than 3",
            "ctx": {"lt": 3.0},
        }
    ]
}


response_less_than_0 = {
    "detail": [
        {
            "type": "less_than",
            "loc": ["path", "item_id"],
            "msg": "Input should be less than 0",
            "ctx": {"lt": 0.0},
        }
    ]
}

response_less_than_equal_3 = {
    "detail": [
        {
            "type": "less_than_equal",
            "loc": ["path", "item_id"],
            "msg": "Input should be less than or equal to 3",
            "ctx": {"le": 3.0},
        }
    ]
}


response_not_valid_pattern = {
    "detail": [
        {
            "ctx": {
                "pattern": "^foo",
            },
            "loc": ["path", "item_id"],
            "msg": "String should match pattern '^foo'",
            "type": "string_pattern_mismatch",
        }
    ]
}


@pytest.mark.parametrize(
    "path,expected_status,expected_response",
    [
        ("/path/foobar", 200, "foobar"),
        ("/path/str/foobar", 200, "foobar"),
        ("/path/str/42", 200, "42"),
        ("/path/str/True", 200, "True"),
        ("/path/int/foobar", 422, response_not_valid_int),
        ("/path/int/True", 422, response_not_valid_int),
        ("/path/int/42", 200, 42),
        ("/path/int/42.5", 422, response_not_valid_int_float),
        ("/path/float/foobar", 422, response_not_valid_float),
        ("/path/float/True", 422, response_not_valid_float),
        ("/path/float/42", 200, 42),
        ("/path/float/42.5", 200, 42.5),
        ("/path/bool/foobar", 422, response_not_valid_bool),
        ("/path/bool/True", 200, True),
        ("/path/bool/42", 422, response_not_valid_bool),
        ("/path/bool/42.5", 422, response_not_valid_bool),
        ("/path/bool/1", 200, True),
        ("/path/bool/0", 200, False),
        ("/path/bool/true", 200, True),
        ("/path/bool/False", 200, False),
        ("/path/bool/false", 200, False),
        ("/path/param/foo", 200, "foo"),
        ("/path/param-required/foo", 200, "foo"),
        ("/path/param-minlength/foo", 200, "foo"),
        ("/path/param-minlength/fo", 422, response_at_least_3),
        ("/path/param-maxlength/foo", 200, "foo"),
        ("/path/param-maxlength/foobar", 422, response_maximum_3),
        ("/path/param-min_maxlength/foo", 200, "foo"),
        ("/path/param-min_maxlength/foobar", 422, response_maximum_3),
        ("/path/param-min_maxlength/f", 422, response_at_least_2),
        ("/path/param-gt/42", 200, 42),
        ("/path/param-gt/2", 422, response_greater_than_3),
        ("/path/param-gt0/0.05", 200, 0.05),
        ("/path/param-gt0/0", 422, response_greater_than_0),
        ("/path/param-ge/42", 200, 42),
        ("/path/param-ge/3", 200, 3),
        ("/path/param-ge/2", 422, response_greater_than_equal_3),
        ("/path/param-lt/42", 422, response_less_than_3),
        ("/path/param-lt/2", 200, 2),
        ("/path/param-lt0/-1", 200, -1),
        ("/path/param-lt0/0", 422, response_less_than_0),
        ("/path/param-le/42", 422, response_less_than_equal_3),
        ("/path/param-le/3", 200, 3),
        ("/path/param-le/2", 200, 2),
        ("/path/param-lt-gt/2", 200, 2),
        ("/path/param-lt-gt/4", 422, response_less_than_3),
        ("/path/param-lt-gt/0", 422, response_greater_than_1),
        ("/path/param-le-ge/2", 200, 2),
        ("/path/param-le-ge/1", 200, 1),
        ("/path/param-le-ge/3", 200, 3),
        ("/path/param-le-ge/4", 422, response_less_than_equal_3),
        ("/path/param-lt-int/2", 200, 2),
        ("/path/param-lt-int/42", 422, response_less_than_3),
        ("/path/param-lt-int/2.7", 422, response_not_valid_int_float),
        ("/path/param-gt-int/42", 200, 42),
        ("/path/param-gt-int/2", 422, response_greater_than_3),
        ("/path/param-gt-int/2.7", 422, response_not_valid_int_float),
        ("/path/param-le-int/42", 422, response_less_than_equal_3),
        ("/path/param-le-int/3", 200, 3),
        ("/path/param-le-int/2", 200, 2),
        ("/path/param-le-int/2.7", 422, response_not_valid_int_float),
        ("/path/param-ge-int/42", 200, 42),
        ("/path/param-ge-int/3", 200, 3),
        ("/path/param-ge-int/2", 422, response_greater_than_equal_3),
        ("/path/param-ge-int/2.7", 422, response_not_valid_int_float),
        ("/path/param-lt-gt-int/2", 200, 2),
        ("/path/param-lt-gt-int/4", 422, response_less_than_3),
        ("/path/param-lt-gt-int/0", 422, response_greater_than_1),
        ("/path/param-lt-gt-int/2.7", 422, response_not_valid_int_float),
        ("/path/param-le-ge-int/2", 200, 2),
        ("/path/param-le-ge-int/1", 200, 1),
        ("/path/param-le-ge-int/3", 200, 3),
        ("/path/param-le-ge-int/4", 422, response_less_than_equal_3),
        ("/path/param-le-ge-int/2.7", 422, response_not_valid_int_float),
        ("/path/param-pattern/foo", 200, "foo"),
        ("/path/param-pattern/fo", 422, response_not_valid_pattern),
    ],
)
def test_get_path(path, expected_status, expected_response):
    response = client.get(path)
    print(path, response.json())
    assert response.status_code == expected_status
    assert response.json() == expected_response


@pytest.mark.parametrize(
    "path,expected_status,expected_response",
    [
        ("/path/param-django-str/42", 200, "42"),
        ("/path/param-django-str/-1", 200, "-1"),
        ("/path/param-django-str/foobar", 200, "foobar"),
        ("/path/param-django-int/0", 200, 0),
        ("/path/param-django-int/42", 200, 42),
        ("/path/param-django-int/42.5", "Cannot resolve", Exception),
        ("/path/param-django-int/-1", "Cannot resolve", Exception),
        ("/path/param-django-int/True", "Cannot resolve", Exception),
        ("/path/param-django-int/foobar", "Cannot resolve", Exception),
        ("/path/param-django-int/not-an-int", 200, "Found not-an-int"),
        # ("/path/param-django-int-str/42", 200, "42"), # https://github.com/pydantic/pydantic/issues/5993
        ("/path/param-django-int-str/42.5", "Cannot resolve", Exception),
        (
            "/path/param-django-slug/django-ninja-is-the-best",
            200,
            "django-ninja-is-the-best",
        ),
        ("/path/param-django-slug/42.5", "Cannot resolve", Exception),
        (
            "/path/param-django-uuid/31ea378c-c052-4b4c-bf0b-679ce5cfcc2a",
            200,
            "31ea378c-c052-4b4c-bf0b-679ce5cfcc2a",
        ),
        (
            "/path/param-django-uuid/31ea378c-c052-4b4c-bf0b-679ce5cfcc2",
            "Cannot resolve",
            Exception,
        ),
        (
            "/path/param-django-uuid-str/31ea378c-c052-4b4c-bf0b-679ce5cfcc2a",
            200,
            "31ea378c-c052-4b4c-bf0b-679ce5cfcc2a",
        ),
        ("/path/param-django-path/some/path/things/after", 200, "some/path/things"),
        ("/path/param-django-path/less/path/after", 200, "less/path"),
        ("/path/param-django-path/plugh/after", 200, "plugh"),
        ("/path/param-django-path//after", "Cannot resolve", Exception),
        ("/path/param-django-custom-int/42", 200, 24),
        ("/path/param-django-custom-int/x42", "Cannot resolve", Exception),
        ("/path/param-django-custom-float/42", 200, 0.24),
        ("/path/param-django-custom-float/x42", "Cannot resolve", Exception),
    ],
)
def test_get_path_django(path, expected_status, expected_response):
    if expected_response is Exception:
        with pytest.raises(Exception, match=expected_status):
            client.get(path)
    else:
        response = client.get(path)
        print(response.json())
        assert response.status_code == expected_status
        assert response.json() == expected_response


def test_path_signature_asserts_default():
    test_router = Router()

    match = "'item_id' is a path param, default not allowed"
    with pytest.raises(AssertionError, match=match):

        @test_router.get("/path/{item_id}")
        def get_path_item_id(request, item_id="1"):
            pass


def test_path_signature_warns_missing():
    test_router = Router()

    match = (
        r"Field\(s\) \('a_path_param', 'another_path_param'\) are in "
        r"the view path, but were not found in the view signature."
    )
    with pytest.warns(UserWarning, match=match):

        @test_router.get("/path/{a_path_param}/{another_path_param}")
        def get_path_item_id(request):
            pass
