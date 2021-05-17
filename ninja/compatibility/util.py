from typing import Any, Optional

try:
    from typing import get_origin  # type: ignore
except ImportError:  # pragma: no coverage

    def get_origin(tp: Any) -> Optional[Any]:
        "typing.get_origin introduced in python3.8"
        return getattr(tp, "__origin__", None)
