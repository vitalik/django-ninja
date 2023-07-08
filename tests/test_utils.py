import pytest

from ninja import NinjaAPI, Query
from ninja.utils import contribute_operation_args, replace_path_param_notation


@pytest.mark.parametrize(
    "input,expected_output",
    [
        ("abc/{def}", "abc/<def>"),
        ("abc/<def>", "abc/<def>"),
        ("abc", "abc"),
        ("<abc>", "<abc>"),
        ("{abc}", "<abc>"),
        ("{abc}/{def}", "<abc>/<def>"),
    ],
)
def test_replace_path_param_notation(input, expected_output):
    assert replace_path_param_notation(input) == expected_output


def test_contribute_operation_args():
    def some_func():
        pass

    contribute_operation_args(some_func, "arg1", str, Query(...))
    contribute_operation_args(some_func, "arg2", int, Query(...))

    api = NinjaAPI()

    api.get("/test")(some_func)

    schema = api.get_openapi_schema()
    assert schema["paths"]["/api/test"]["get"]["parameters"] == [
        {
            "in": "query",
            "name": "arg1",
            "schema": {"title": "Arg1", "type": "string"},
            "required": True,
        },
        {
            "in": "query",
            "name": "arg2",
            "schema": {"title": "Arg2", "type": "integer"},
            "required": True,
        },
    ]
