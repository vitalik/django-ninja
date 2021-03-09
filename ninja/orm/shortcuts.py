from typing import Any, List

from ninja.orm.factory import create_schema

# GOAL:
# from ninja.orm import S, L
# S(Job) -> JobSchema? Job?
# S(Job) -> should reuse already created schema
# S(Job, fields='xxx') -> new schema ? how to name Job1 , 2, 3 and so on ?
# L(Job) -> List[Job]


def S(model: Any, **kwargs):
    return create_schema(model, **kwargs)


def L(model: Any, **kwargs):
    schema = S(model, **kwargs)
    return List[schema]
