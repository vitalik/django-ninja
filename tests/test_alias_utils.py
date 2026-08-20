"""
Direct unit tests for the PEP 695 type-alias helpers in
``ninja.compatibility.util``.

These helpers are consumed by:
- ``ninja.signature.details.is_collection_type`` (collection detection)
- ``ninja.filter_schema.FilterSchema._get_filter_lookup`` (FilterLookup recovery)
- ``ninja.pagination._find_collection_response`` (pagination element extraction)

``ninja/compatibility/*`` is excluded from coverage measurement
(``pyproject.toml`` ``[tool.coverage.run] omit``), so these tests verify
correctness directly rather than via the coverage gate. The consumer-level
regression tests in ``test_filter_schema.py``, ``test_signature_details.py``,
and ``test_pagination_router.py`` exercise the helpers through the public API.

``TypeAliasType(...)`` is used instead of the ``type X = ...`` statement so
this file imports on Python < 3.12 (the ``type`` statement is 3.12+ syntax,
but the runtime ``TypeAliasType`` object is available via ``typing_extensions``
on earlier versions).
"""

import typing
from typing import Annotated, List, Optional, Set, Tuple, TypeVar

from typing_extensions import TypeAliasType

from ninja.compatibility.util import (
    TYPE_ALIAS_TYPES,
    collect_alias_metadata,
    get_collection_item,
    unwrap_type_alias,
)


class Book:
    pass


class Author:
    pass


T = TypeVar("T")
U = TypeVar("U")


# ---------------------------------------------------------------------------
# 1. Bare aliases
# ---------------------------------------------------------------------------


def test_unwrap_type_alias_bare_alias():
    """A bare ``type X = List[Book]`` alias unwraps to ``List[Book]``."""
    BareListAlias = TypeAliasType("BareListAlias", List[Book])
    assert unwrap_type_alias(BareListAlias) == List[Book]


def test_collect_alias_metadata_bare_alias_without_annotated():
    """A bare alias whose value is not ``Annotated`` yields no metadata."""
    BareListAlias = TypeAliasType("BareListAlias", List[Book])
    assert collect_alias_metadata(BareListAlias) == []


def test_get_collection_item_bare_alias():
    """A bare ``type X = List[Book]`` alias resolves to ``Book``."""
    BareListAlias = TypeAliasType("BareListAlias", List[Book])
    assert get_collection_item(BareListAlias) is Book


def test_get_collection_item_bare_alias_to_annotated():
    """A bare ``type X = Annotated[List[Book], ...]`` resolves to ``Book``."""
    AnnListAlias = TypeAliasType("AnnListAlias", Annotated[List[Book], "meta"])
    assert get_collection_item(AnnListAlias) is Book


# ---------------------------------------------------------------------------
# 2. Chained aliases
# ---------------------------------------------------------------------------


def test_unwrap_type_alias_chained_alias():
    """``type Inner = ...; type Outer = Inner`` unwraps Outer to Inner's value."""
    Inner = TypeAliasType("Inner", Annotated[Optional[List[str]], "inner"])
    Outer = TypeAliasType("Outer", Inner)
    assert unwrap_type_alias(Outer) == Annotated[Optional[List[str]], "inner"]


def test_collect_alias_metadata_chained_alias():
    """Metadata on an inner alias is recovered through a chained outer alias."""
    Inner = TypeAliasType("Inner", Annotated[Optional[List[str]], "inner_meta"])
    Outer = TypeAliasType("Outer", Inner)
    assert collect_alias_metadata(Outer) == ["inner_meta"]


def test_get_collection_item_chained_alias():
    """A chained alias resolves to the concrete element type."""
    Inner = TypeAliasType("Inner", Annotated[Optional[List[str]], "inner"])
    Outer = TypeAliasType("Outer", Inner)
    assert get_collection_item(Outer) is str


# ---------------------------------------------------------------------------
# 3. Parameterized aliases and type-variable substitution
# ---------------------------------------------------------------------------


def test_unwrap_type_alias_parameterized_generic_is_structural():
    """``unwrap_type_alias`` is structural: ``Names[Book]`` unwraps to the
    alias's ``__value__`` with ``T`` left unresolved (substitution is the job
    of ``get_collection_item``)."""
    NamesGeneric = TypeAliasType(
        "NamesGeneric", Annotated[List[T], "meta"], type_params=(T,)
    )
    parameterized = NamesGeneric[Book]
    # T is unresolved here; only get_collection_item resolves it.
    assert unwrap_type_alias(parameterized) == Annotated[List[T], "meta"]


def test_get_collection_item_parameterized_generic_resolves_typevar():
    """``Names[Book]`` resolves ``T`` to ``Book`` and returns ``Book``."""
    NamesGeneric = TypeAliasType("NamesGeneric", List[T], type_params=(T,))
    assert get_collection_item(NamesGeneric[Book]) is Book


def test_get_collection_item_parameterized_generic_with_annotated():
    """``Names[Book]`` where the value is ``Annotated[List[T], ...]`` resolves
    ``T`` to ``Book`` and returns ``Book``."""
    NamesGeneric = TypeAliasType(
        "NamesGeneric", Annotated[List[T], "meta"], type_params=(T,)
    )
    assert get_collection_item(NamesGeneric[Book]) is Book


def test_collect_alias_metadata_parameterized_generic():
    """Metadata on a parameterized generic alias is recovered."""
    NamesGeneric = TypeAliasType(
        "NamesGeneric", Annotated[List[T], "meta"], type_params=(T,)
    )
    assert collect_alias_metadata(NamesGeneric[Book]) == ["meta"]


# ---------------------------------------------------------------------------
# 4. Annotated traversal
# ---------------------------------------------------------------------------


def test_collect_alias_metadata_annotated_top_level():
    """``Annotated[List[str], "meta"]`` yields ``["meta"]``."""
    assert collect_alias_metadata(Annotated[List[str], "meta"]) == ["meta"]


def test_collect_alias_metadata_annotated_multiple_metadata():
    """Multiple metadata items on a single ``Annotated`` are all collected,
    inner-first (left-to-right per PEP 593)."""
    ann = Annotated[List[str], "a", "b"]
    assert collect_alias_metadata(ann) == ["a", "b"]


def test_collect_alias_metadata_pep593_flattened_nested_annotated():
    """``Annotated[Annotated[T, inner], outer]`` is flattened by ``typing`` to
    ``Annotated[T, inner, outer]``; metadata is ``[inner, outer]``."""
    flat = Annotated[Annotated[List[str], "inner"], "outer"]
    assert collect_alias_metadata(flat) == ["inner", "outer"]


def test_get_collection_item_annotated():
    """``Annotated[List[Book], ...]`` resolves to ``Book``."""
    assert get_collection_item(Annotated[List[Book], "meta"]) is Book


# ---------------------------------------------------------------------------
# 5. Union traversal
# ---------------------------------------------------------------------------


def test_get_collection_item_optional_list():
    """``Optional[List[Book]]`` resolves to ``Book``."""
    assert get_collection_item(Optional[List[Book]]) is Book


def test_get_collection_item_union_of_scalars_returns_none():
    """``Union[str, int]`` has no collection member; returns ``None``."""
    assert get_collection_item(typing.Union[str, int]) is None


def test_get_collection_item_union_of_list_and_scalar():
    """``Union[List[Book], str]`` resolves to ``Book`` (the collection member)."""
    assert get_collection_item(typing.Union[List[Book], str]) is Book


def test_get_collection_item_optional_list_alias():
    """``type X = Optional[List[Book]]`` resolves to ``Book``."""
    Alias = TypeAliasType("Alias", Optional[List[Book]])
    assert get_collection_item(Alias) is Book


# ---------------------------------------------------------------------------
# 6. Inner-first metadata order
# ---------------------------------------------------------------------------


def test_collect_alias_metadata_inner_first_order():
    """For ``type Inner = Annotated[List[str], inner]; type Outer = Annotated[
    Inner, outer]``, metadata is ``[inner, outer]`` (inner-first), matching the
    PEP 593 flattening of ``Annotated[Annotated[List[str], inner], outer]`` to
    ``Annotated[List[str], inner, outer]``."""
    Inner = TypeAliasType("Inner", Annotated[List[str], "inner"])
    Outer = TypeAliasType("Outer", Annotated[Inner, "outer"])
    assert collect_alias_metadata(Outer) == ["inner", "outer"]


def test_collect_alias_metadata_inner_first_three_level_chain():
    """A three-level chain preserves inner-first order across all levels."""
    L1 = TypeAliasType("L1", Annotated[List[str], "a"])
    L2 = TypeAliasType("L2", Annotated[L1, "b"])
    L3 = TypeAliasType("L3", Annotated[L2, "c"])
    assert collect_alias_metadata(L3) == ["a", "b", "c"]


def test_collect_alias_metadata_inner_first_with_outer_metadata_only():
    """When the outer alias has no ``Annotated`` wrapper of its own but its
    inner alias does, only the inner metadata is collected (no outer metadata
    exists to append)."""
    Inner = TypeAliasType("Inner", Annotated[List[str], "inner"])
    Outer = TypeAliasType("Outer", Inner)
    assert collect_alias_metadata(Outer) == ["inner"]


# ---------------------------------------------------------------------------
# 7. Strict element-metadata boundary
# ---------------------------------------------------------------------------


def test_collect_alias_metadata_does_not_descend_into_list_elements():
    """Metadata attached to a list element type (``List[Annotated[str, ...]]``)
    is NOT collected; only the outer ``Annotated`` wrapper's metadata is."""
    patho = Annotated[List[Annotated[str, "should_NOT_be_collected"]], "outer"]
    assert collect_alias_metadata(patho) == ["outer"]


def test_collect_alias_metadata_boundary_with_alias_wrapper():
    """The boundary holds when the outer wrapper is an alias: metadata on the
    list element of the alias's value is not surfaced."""
    Alias = TypeAliasType("Alias", Annotated[List[Annotated[str, "elem"]], "outer"])
    assert collect_alias_metadata(Alias) == ["outer"]


def test_collect_alias_metadata_does_not_descend_into_set_elements():
    """The boundary holds for ``Set`` as well as ``List``."""
    patho = Annotated[Set[Annotated[str, "elem"]], "outer"]
    assert collect_alias_metadata(patho) == ["outer"]


def test_collect_alias_metadata_does_not_descend_into_tuple_elements():
    """The boundary holds for ``Tuple`` as well."""
    patho = Annotated[Tuple[Annotated[str, "elem"]], "outer"]
    assert collect_alias_metadata(patho) == ["outer"]


# ---------------------------------------------------------------------------
# 8. Bare unparameterized collections
# ---------------------------------------------------------------------------


def test_get_collection_item_bare_list_returns_none():
    """A bare ``list`` with no element argument returns ``None``."""
    assert get_collection_item(list) is None


def test_get_collection_item_bare_typing_list_returns_none():
    """A bare ``typing.List`` with no element argument returns ``None``."""
    assert get_collection_item(List) is None


def test_get_collection_item_bare_set_returns_none():
    assert get_collection_item(set) is None


def test_get_collection_item_bare_typing_set_returns_none():
    assert get_collection_item(typing.Set) is None


def test_get_collection_item_bare_tuple_returns_none():
    assert get_collection_item(tuple) is None


def test_get_collection_item_bare_typing_tuple_returns_none():
    assert get_collection_item(typing.Tuple) is None


def test_get_collection_item_scalar_returns_none():
    """A non-collection scalar type returns ``None``."""
    assert get_collection_item(str) is None
    assert get_collection_item(int) is None
    assert get_collection_item(Book) is None


def test_get_collection_item_object_instance_returns_none():
    """A non-type instance returns ``None``."""
    assert get_collection_item(object()) is None


def test_get_collection_item_newtype_returns_none():
    """``NewType`` is not a collection; returns ``None``."""
    NewStr = typing.NewType("NewStr", str)
    assert get_collection_item(NewStr) is None


# ---------------------------------------------------------------------------
# Sanity: TYPE_ALIAS_TYPES is populated
# ---------------------------------------------------------------------------


def test_type_alias_types_is_non_empty_tuple():
    """``TYPE_ALIAS_TYPES`` must contain at least the ``typing_extensions``
    backport so ``isinstance`` checks work on every supported Python."""
    assert isinstance(TYPE_ALIAS_TYPES, tuple)
    assert len(TYPE_ALIAS_TYPES) >= 1
    assert all(isinstance(t, type) for t in TYPE_ALIAS_TYPES)
