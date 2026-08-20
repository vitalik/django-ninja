import typing
from sys import version_info
from typing import List, Optional, TypeVar

import pytest
from typing_extensions import Annotated, TypeAliasType

from ninja.signature.details import is_collection_type

_T = TypeVar("_T")


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
        # PEP 695 `type` aliases (TypeAliasType is available via typing_extensions
        # on every supported Python; the `type` statement itself is 3.12+ syntax).
        pytest.param(
            TypeAliasType("BareListAlias", List[str]),
            True,
            id="true_for_bare_list_type_alias",
        ),
        pytest.param(
            TypeAliasType("AnnotatedListAlias", Annotated[List[str], "meta"]),
            True,
            id="true_for_annotated_list_type_alias",
        ),
        pytest.param(
            TypeAliasType(
                "Inner",
                Annotated[Optional[List[str]], "inner"],
            ),
            True,
            id="true_for_inner_list_type_alias",
        ),
        pytest.param(
            TypeAliasType(
                "Outer",
                TypeAliasType(
                    "InnerForOuter",
                    Annotated[Optional[List[str]], "inner"],
                ),
            ),
            True,
            id="true_for_chained_list_type_alias",
        ),
        pytest.param(
            TypeAliasType(
                "NamesGeneric",
                Annotated[List[_T], "meta"],
                type_params=(_T,),
            )[str],
            True,
            id="true_for_parameterized_generic_list_type_alias",
        ),
        pytest.param(
            TypeAliasType("ScalarAlias", Optional[str]),
            False,
            id="false_for_scalar_type_alias",
        ),
        pytest.param(
            TypeAliasType("BareScalarAlias", str),
            False,
            id="false_for_bare_scalar_type_alias",
        ),
    ],
)
def test_is_collection_type_returns(annotation: typing.Any, expected: bool):
    assert is_collection_type(annotation) is expected
