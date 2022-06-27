from typing import Any, Dict

__all__ = ["NOT_SET"]


class NOT_SET_TYPE:
    def __repr__(self) -> str:  # pragma: no cover
        return f"{__name__}.{self.__class__.__name__}"

    def __copy__(self) -> Any:
        return NOT_SET

    def __deepcopy__(self, memodict: Dict = {}) -> Any:
        return NOT_SET


NOT_SET = NOT_SET_TYPE()
