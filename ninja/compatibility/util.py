from typing import Any, Optional, Union

# python3.8+ get_origin, get_args
try:
    from typing import get_args, get_origin  # type: ignore
except ImportError:  # pragma: no coverage

    def get_origin(tp: Any) -> Optional[Any]:
        "typing.get_origin introduced in python3.8"
        return getattr(tp, "__origin__", None)

    def get_args(tp: Any) -> Optional[Any]:
        "typing.get_args introduced in python3.8"
        return getattr(tp, "__args__", None)


# python3.10+ syntax of creating a union or optional type (with str | int)
# UNION_TYPES allows to check both universes if types are a union
try:
    from types import UnionType

    UNION_TYPES = (Union, UnionType)
except ImportError:
    UNION_TYPES = (Union,)

__all__ = ["get_origin", "get_args"]
