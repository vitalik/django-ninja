from typing import Any, Dict

__all__ = ["NOT_SET"]


class NOT_SET:
    def __copy__(self) -> Any:
        return NOT_SET

    def __deepcopy__(self, memodict: Dict = {}) -> Any:
        return NOT_SET


NOT_SET: Any = NOT_SET()  # type: ignore  # noqa: F811
