from typing import Any, Optional

try:
    from typing import get_args, get_origin  # type: ignore
except ImportError:  # pragma: no coverage

    def get_origin(tp: Any) -> Optional[Any]:
        "typing.get_origin introduced in python3.8"
        return getattr(tp, "__origin__", None)

    def get_args(tp: Any) -> Optional[Any]:
        "typing.get_args introduced in python3.8"
        return getattr(tp, "__args__", None)


__all__ = ["get_origin", "get_args"]
