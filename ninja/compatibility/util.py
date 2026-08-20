import sys
from typing import Any, List, Optional, Set, Tuple, TypeVar, Union

from typing_extensions import Annotated, get_args, get_origin

__all__ = [
    "UNION_TYPES",
    "TYPE_ALIAS_TYPES",
    "get_annotations_from_namespace",
    "unwrap_type_alias",
    "collect_alias_metadata",
    "get_collection_item",
]


# python3.10+ syntax of creating a union or optional type (with str | int)
# UNION_TYPES allows to check both universes if types are a union
try:
    from types import UnionType

    UNION_TYPES = (Union, UnionType)
except ImportError:
    UNION_TYPES = (Union,)


# python3.12+ `type X = ...` syntax (PEP 695) produces a TypeAliasType.
# typing_extensions also backports it, and the two classes are not identical,
# so collect every variant available to check against with isinstance().
_alias_types = []
for _module in ("typing", "typing_extensions"):
    try:
        _alias = getattr(__import__(_module), "TypeAliasType", None)
    except ImportError:  # pragma: no cover
        _alias = None
    if _alias is not None and _alias not in _alias_types:
        _alias_types.append(_alias)
TYPE_ALIAS_TYPES: Tuple[Any, ...] = tuple(_alias_types)


# Collection origins used by get_collection_item. Kept here so the helper does
# not import from ninja.signature.details (which would create a cycle through
# ninja.params.models -> ninja.signature.details).
_COLLECTION_TYPES: Tuple[Any, ...] = (List, list, set, tuple)


def _is_type_alias(annotation: Any) -> bool:
    return isinstance(annotation, TYPE_ALIAS_TYPES)


def _is_type_alias_origin(origin: Any) -> bool:
    return isinstance(origin, TYPE_ALIAS_TYPES)


def _substitute(annotation: Any, subst: dict) -> Any:
    """Substitute TypeVars in ``annotation`` using the ``subst`` mapping.

    Used to resolve the type parameters of a parameterized generic
    ``TypeAliasType`` (PEP 695) so that ``Names[Book]`` resolves to a
    value whose ``List[T]`` becomes ``List[Book]``.
    """
    if isinstance(annotation, TypeVar) and annotation in subst:
        return subst[annotation]
    origin = get_origin(annotation)
    args = get_args(annotation)
    if not args:
        return annotation
    if origin is Annotated:
        return Annotated[(_substitute(args[0], subst),) + args[1:]]
    new_args = tuple(_substitute(a, subst) for a in args)
    try:
        if len(new_args) == 1:
            return List[new_args[0]] if origin is list else origin[new_args[0]]
        return origin[new_args]
    except Exception:  # pragma: no cover - defensive
        try:
            return annotation.copy_with(new_args)  # type: ignore[attr-defined]
        except Exception:
            return annotation


def unwrap_type_alias(annotation: Any, seen: Optional[Set[int]] = None) -> Any:
    """Structurally unwrap PEP 695 ``type`` aliases.

    Recursively follows ``TypeAliasType.__value__`` and parameterized generic
    alias origins (where ``get_origin(annotation)`` is a ``TypeAliasType``).
    Stops at the first non-alias annotation. Type parameters are NOT resolved
    here; use :func:`get_collection_item` when the concrete element type is
    needed.

    ``seen`` is a defensive guard keyed by ``id()``. ``TypeAliasType.__value__``
    is immutable, so a genuine runtime cycle is not constructible, but the guard
    keeps the function total on any input.
    """
    if _is_type_alias(annotation):
        if seen is None:
            seen = set()
        if id(annotation) in seen:
            return annotation
        seen.add(id(annotation))
        return unwrap_type_alias(annotation.__value__, seen)
    origin = get_origin(annotation)
    if _is_type_alias_origin(origin):
        if seen is None:
            seen = set()
        if id(origin) in seen:
            return annotation
        seen.add(id(origin))
        return unwrap_type_alias(origin.__value__, seen)
    return annotation


def collect_alias_metadata(
    annotation: Any, seen: Optional[Set[int]] = None
) -> List[Any]:
    """Collect ``Annotated`` metadata from a (possibly chained) type alias.

    Walks the top-level chain of ``TypeAliasType.__value__``,
    parameterized-generic alias origins, and ``Annotated`` wrappers. Order is
    inner-first to match PEP 593 flattening: ``Annotated[Annotated[T, inner],
    outer]`` flattens to ``Annotated[T, inner, outer]``, so the inner alias's
    metadata is emitted before the outer wrapper's metadata.

    The traversal has a strict boundary: it does NOT descend into collection
    element types (``List[Annotated[str, ...]]``), so metadata attached to an
    element is not surfaced as if it belonged to the outer field.

    Returns an empty list for a bare alias without ``Annotated``. ``seen`` is a
    defensive cycle guard (see :func:`unwrap_type_alias`).
    """
    if seen is None:
        seen = set()
    if _is_type_alias(annotation):
        if id(annotation) in seen:
            return []
        seen.add(id(annotation))
        value = annotation.__value__
        value_origin = get_origin(value)
        if value_origin is Annotated:
            value_args = get_args(value)
            out = list(collect_alias_metadata(value_args[0], seen))
            out.extend(value_args[1:])
            return out
        return collect_alias_metadata(value, seen)
    origin = get_origin(annotation)
    if _is_type_alias_origin(origin):
        if id(origin) in seen:
            return []
        seen.add(id(origin))
        return collect_alias_metadata(origin.__value__, seen)
    if origin is Annotated:
        args = get_args(annotation)
        out = list(collect_alias_metadata(args[0], seen))
        out.extend(args[1:])
        return out
    return []


def get_collection_item(annotation: Any) -> Optional[Any]:
    """Return the concrete element type of a collection annotation.

    Unwraps ``TypeAliasType`` chains, parameterized generic aliases (resolving
    type parameters via :func:`_substitute`), ``Annotated`` wrappers, and
    ``Union`` types. Returns the element type for shapes like ``List[Book]``,
    ``Annotated[List[Book], ...]``, ``Optional[List[Book]]``, and their
    alias-equivalents. Returns ``None`` for bare unparameterized collections
    (``list``, ``typing.List``), non-collection types, or unresolvable cases.
    """
    if _is_type_alias(annotation):
        return get_collection_item(annotation.__value__)
    origin = get_origin(annotation)
    if _is_type_alias_origin(origin):
        value = origin.__value__
        type_params = getattr(origin, "__type_params__", ())
        type_args = get_args(annotation)
        subst = dict(zip(type_params, type_args))
        return get_collection_item(_substitute(value, subst))
    if origin is Annotated:
        return get_collection_item(get_args(annotation)[0])
    if origin in UNION_TYPES:
        for arg in get_args(annotation):
            if get_collection_item(arg) is not None:
                return get_collection_item(arg)
        return None
    if origin in _COLLECTION_TYPES:
        args = get_args(annotation)
        return args[0] if args else None
    if origin is None:
        return None
    return None


# python3.14+ no longer puts __annotations__ in the class namespace dict
# during metaclass __new__; instead an __annotate__ function is used (PEP 749)
if sys.version_info >= (3, 14):
    import annotationlib

    def get_annotations_from_namespace(namespace: dict) -> dict:
        ann = annotationlib.get_annotate_from_class_namespace(namespace)
        if ann is not None:
            return annotationlib.call_annotate_function(
                ann, format=annotationlib.Format.VALUE
            )
        return namespace.get("__annotations__", {})

else:

    def get_annotations_from_namespace(namespace: dict) -> dict:
        return namespace.get("__annotations__", {})
