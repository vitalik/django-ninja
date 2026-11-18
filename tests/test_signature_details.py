import typing

import pytest

from ninja.signature.details import is_collection_type

# The legacy typing aliases (typing.List, ...) are tested on purpose: user code may
# still use them, so they must keep being detected as collections.


@pytest.mark.parametrize(
    ("annotation", "expected"),
    [
        pytest.param(typing.List, True, id="true_for_typing_List"),  # noqa: UP006
        pytest.param(list, True, id="true_for_native_list"),
        pytest.param(typing.Set, True, id="true_for_typing_Set"),  # noqa: UP006
        pytest.param(set, True, id="true_for_native_set"),
        pytest.param(typing.Tuple, True, id="true_for_typing_Tuple"),  # noqa: UP006
        pytest.param(tuple, True, id="true_for_native_tuple"),
        pytest.param(
            typing.Optional[typing.List[str]],  # noqa: UP006
            True,
            id="true_for_optional_typing_list",
        ),
        pytest.param(typing.Optional[list[str]], True, id="true_for_optional_list"),
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
        pytest.param(list[int], True, id="true_for_parameterized_native_list"),
        pytest.param(set[int], True, id="true_for_parameterized_native_set"),
        pytest.param(tuple[int], True, id="true_for_parameterized_native_tuple"),
    ],
)
def test_is_collection_type_returns(annotation: typing.Any, expected: bool):
    assert is_collection_type(annotation) is expected
