from typing import Type, Iterable, Callable, Any
from django.core.files.uploadedfile import UploadedFile as DjangoUploadedFile


class UploadedFile(DjangoUploadedFile):
    @classmethod
    def __get_validators__(cls: Type["UploadedFile"]) -> Iterable[Callable[..., Any]]:
        yield cls.validate

    @classmethod
    def validate(cls: Type["UploadedFile"], v: Any) -> Any:
        if not isinstance(v, DjangoUploadedFile):
            raise ValueError(f"Expected UploadFile, received: {type(v)}")
        return v
