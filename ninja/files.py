from typing import Any, Callable, Dict

from django.core.files.uploadedfile import UploadedFile as DjangoUploadedFile
from pydantic_core import core_schema

__all__ = ["UploadedFile"]


class UploadedFile(DjangoUploadedFile):
    @classmethod
    def __get_pydantic_json_schema__(cls, core_schema: Any, handler: Callable) -> Dict:
        # calling handler(core_schema) here raises an exception
        json_schema: Dict[str, str] = {}
        json_schema.update(type="string", format="binary")
        return json_schema

    @classmethod
    def _validate(cls, v: Any, _: Any) -> Any:
        if not isinstance(v, DjangoUploadedFile):
            raise ValueError(f"Expected UploadFile, received: {type(v)}")
        return v

    @classmethod
    def __get_pydantic_core_schema__(cls, source: Any, handler: Callable) -> Any:
        return core_schema.with_info_plain_validator_function(cls._validate)
