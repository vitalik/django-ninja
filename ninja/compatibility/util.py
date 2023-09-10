from typing import Callable, Union

import django

__all__ = ["async_to_sync", "UNION_TYPES"]


# python3.10+ syntax of creating a union or optional type (with str | int)
# UNION_TYPES allows to check both universes if types are a union
try:
    from types import UnionType

    UNION_TYPES = (Union, UnionType)
except ImportError:
    UNION_TYPES = (Union,)


if django.VERSION < (3, 1):  # pragma: no cover

    def async_to_sync(func: Callable) -> Callable:
        raise NotImplementedError("Django<3.1 does not have async support")

else:
    from asgiref.sync import async_to_sync
