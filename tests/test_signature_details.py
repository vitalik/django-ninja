import typing
from sys import version_info

import pytest
from pydantic import BaseModel

from ninja.signature.details import (
    extract_pydantic_model_from_union,
    is_collection_type,
)


class SampleModel(BaseModel):
    """Sample model for testing extract_pydantic_model_from_union."""

    value: int


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


@pytest.mark.parametrize(
    ("annotation", "expected"),
    [
        pytest.param(
            SampleModel,
            None,
            id="returns_none_for_non_union_type",
        ),
        pytest.param(
            typing.Optional[SampleModel],
            SampleModel,
            id="returns_model_from_optional_syntax",
        ),
        # PEP 604 Union syntax (X | Y) requires Python 3.10+
        *(
            (
                pytest.param(
                    SampleModel | None,
                    SampleModel,
                    id="returns_model_from_union_with_none",
                ),
                pytest.param(
                    str | None,
                    None,
                    id="returns_none_when_no_model_in_union",
                ),
                pytest.param(
                    str | int,
                    None,
                    id="returns_none_for_union_without_model",
                ),
            )
            if version_info >= (3, 10)
            else ()
        ),
    ],
)
def test_extract_pydantic_model_from_union_returns(
    annotation: typing.Any, expected: typing.Optional[type]
):
    assert extract_pydantic_model_from_union(annotation) is expected
