import warnings
from typing import Optional

import pytest
from pydantic import BaseModel, ValidationError

from ninja import Schema


class OptModel(BaseModel):
    a: int = None
    b: Optional[int]
    c: Optional[int] = None


class OptSchema(Schema):
    a: int = None
    b: Optional[int]
    c: Optional[int] = None


def test_optional_pydantic_model():
    with pytest.raises(ValidationError):
        OptModel().dict()

    assert OptModel(b=None).model_dump() == {"a": None, "b": None, "c": None}


def test_optional_schema():
    with pytest.raises(ValidationError):
        OptSchema().dict()

    assert OptSchema(b=None).dict() == {"a": None, "b": None, "c": None}


def test_deprecated_schema():
    with warnings.catch_warnings(record=True) as w:
        OptSchema.schema()
    assert w[0].message.args == (".schema() is deprecated, use .json_schema() instead",)
