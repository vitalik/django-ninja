from typing import Any, Callable

from django.core.files.uploadedfile import UploadedFile as DjangoUploadedFile
from pydantic.json_schema import JsonSchemaValue
from pydantic_core import core_schema

__all__ = ["UploadedFile"]


class UploadedFile(DjangoUploadedFile):
    @classmethod
    def __get_pydantic_json_schema__(cls, core_schema, handler):
        # calling handler(core_schema) here raises an exception
        json_schema = {}
        json_schema.update(type="string", format="binary")
        return json_schema

    @classmethod
    def _validate(cls, __input_value: Any, _):
        if not isinstance(__input_value, DjangoUploadedFile):
            raise ValueError(f"Expected UploadFile, received: {type(__input_value)}")
        return __input_value

    @classmethod
    def __get_pydantic_core_schema__(cls, source, handler):
        return core_schema.general_plain_validator_function(cls._validate)
