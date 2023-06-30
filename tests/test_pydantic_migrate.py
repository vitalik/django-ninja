import pytest
from typing import Optional
from ninja import Schema
from pydantic import BaseModel, ValidationError


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

    assert OptModel(b=None).dict() == {"a": None, "b": None, "c": None}


def test_optional_schema():
    with pytest.raises(ValidationError):
        OptSchema().dict()

    assert OptSchema(b=None).dict() == {"a": None, "b": None, "c": None}
