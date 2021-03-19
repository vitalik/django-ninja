from typing import Any, List, Type

from ninja import Schema
from ninja.orm.factory import create_schema

__all__ = ["S", "L"]


# GOAL:
# from ninja.orm import S, L
# S(Job) -> JobSchema? Job?
# S(Job) -> should reuse already created schema
# S(Job, fields='xxx') -> new schema ? how to name Job1 , 2, 3 and so on ?
# L(Job) -> List[Job]


def S(model: Any, **kwargs: Any) -> Type[Schema]:
    return create_schema(model, **kwargs)


def L(model: Any, **kwargs: Any) -> List[Any]:
    schema = S(model, **kwargs)
    return List[schema]  # type: ignore
