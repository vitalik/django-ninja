from typing import Any, Callable, Dict, Iterable, Optional, Type

from django.core.files.uploadedfile import UploadedFile as DjangoUploadedFile
from pydantic.fields import ModelField

__all__ = ["UploadedFile"]


class UploadedFile(DjangoUploadedFile):
    @classmethod
    def __get_validators__(cls: Type["UploadedFile"]) -> Iterable[Callable[..., Any]]:
        yield cls._validate

    @classmethod
    def _validate(cls: Type["UploadedFile"], v: Any) -> Any:
        if not isinstance(v, DjangoUploadedFile):
            raise ValueError(f"Expected UploadFile, received: {type(v)}")
        return v

    @classmethod
    def __modify_schema__(
        cls, field_schema: Dict[str, Any], field: Optional[ModelField] = None
    ) -> None:
        field_schema.update(type="string", format="binary")
