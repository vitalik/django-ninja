import sys
from typing import Union

__all__ = ["UNION_TYPES", "get_annotations_from_namespace"]


# python3.10+ syntax of creating a union or optional type (with str | int)
# UNION_TYPES allows to check both universes if types are a union
try:
    from types import UnionType

    UNION_TYPES = (Union, UnionType)
except ImportError:
    UNION_TYPES = (Union,)


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
