from enum import Enum
from typing import Any, Dict, Optional

__all__ = ["NOT_SET", "DecoratorMode"]


class NOT_SET_TYPE:
    def __repr__(self) -> str:  # pragma: no cover
        return f"{__name__}.{self.__class__.__name__}"

    def __copy__(self) -> Any:
        return NOT_SET

    def __deepcopy__(self, memodict: Optional[Dict] = None) -> Any:
        return NOT_SET


NOT_SET = NOT_SET_TYPE()


class DecoratorMode(str, Enum):
    """Mode for decorator application in add_decorator method"""

    OPERATION = "operation"  # Apply decorator to operation.run (after validation)
    VIEW = "view"  # Apply decorator to Django view (before validation)
