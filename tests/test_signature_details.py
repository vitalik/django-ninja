from __future__ import annotations

import typing
from functools import wraps
from sys import version_info

import pytest

from ninja import NinjaAPI, Schema
from ninja.signature.details import ViewSignature, is_collection_type


@pytest.mark.parametrize(
    ("annotation", "expected"),
    [
        pytest.param(typing.List, True, id="true_for_typing_List"),
        pytest.param(list, True, id="true_for_native_list"),
        pytest.param(typing.Set, True, id="true_for_typing_Set"),
        pytest.param(set, True, id="true_for_native_set"),
        pytest.param(typing.Tuple, True, id="true_for_typing_Tuple"),
        pytest.param(tuple, True, id="true_for_native_tuple"),
        pytest.param(
            typing.Optional[typing.List[str]], True, id="true_for_optional_list"
        ),
        pytest.param(
            type("Custom", (), {}),
            False,
            id="false_for_custom_type_without_typing_origin",
        ),
        pytest.param(
            object(), False, id="false_for_custom_instance_without_typing_origin"
        ),
        pytest.param(
            typing.NewType("SomethingNew", str),
            False,
            id="false_for_instance_without_typing_origin",
        ),
        # Can't mark with `pytest.mark.skipif` since we'd attempt to instantiate the
        # parameterized value/type(e.g. `list[int]`). Which only works with Python >= 3.9)
        *(
            (
                pytest.param(list[int], True, id="true_for_parameterized_native_list"),
                pytest.param(set[int], True, id="true_for_parameterized_native_set"),
                pytest.param(
                    tuple[int], True, id="true_for_parameterized_native_tuple"
                ),
            )
            # TODO: Remove conditional once support for <=3.8 is dropped
            if version_info >= (3, 9)
            else ()
        ),
    ],
)
def test_is_collection_type_returns(annotation: typing.Any, expected: bool):
    assert is_collection_type(annotation) is expected


class PayloadSchema(Schema):
    name: str
    value: int


def test_parameter_model_has_view_module():
    """Parameter models must inherit __module__ from view function."""
    api = NinjaAPI()

    @api.post("/test")
    def view(request, payload: PayloadSchema):
        return {}

    signature = ViewSignature("/test", view)
    body_model = next(m for m in signature.models if m.__ninja_param_source__ == "body")

    assert body_model.__module__ == view.__module__
    assert body_model.__module__ == __name__


def test_decorated_function_resolves_string_annotations():
    """Decorated functions with string annotations must resolve correctly."""
    api = NinjaAPI()

    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            return func(*args, **kwargs)

        return wrapper

    @api.post("/test")
    @decorator
    def view(request, payload: PayloadSchema):
        return {}

    signature = ViewSignature("/test", view)

    body_model = next(
        (m for m in signature.models if m.__ninja_param_source__ == "body"), None
    )
    query_model = next(
        (m for m in signature.models if m.__ninja_param_source__ == "query"), None
    )

    assert body_model is not None
    assert query_model is None
