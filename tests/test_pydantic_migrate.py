import warnings
from typing import Optional

import pytest
from django.db import models
from pydantic import BaseModel, ValidationError

from ninja import ModelSchema, Schema


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


def test_orm_config():
    class SomeCustomModel(models.Model):
        f1 = models.CharField()
        f2 = models.CharField(blank=True, null=True)

        class Meta:
            app_label = "tests"

    class SomeCustomSchema(ModelSchema):
        f3: int
        f4: int = 1
        _private: str = "<secret>"  # private should be ignored

        class Meta:
            model = SomeCustomModel
            fields = ["f1", "f2"]

    assert SomeCustomSchema.json_schema() == {
        "title": "SomeCustomSchema",
        "type": "object",
        "properties": {
            "f1": {"title": "F1", "type": "string"},
            "f2": {"anyOf": [{"type": "string"}, {"type": "null"}], "title": "F2"},
            "f3": {"title": "F3", "type": "integer"},
            "f4": {"title": "F4", "default": 1, "type": "integer"},
        },
        "required": ["f3", "f1"],
    }
