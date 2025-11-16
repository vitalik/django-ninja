import copy
from typing import (
    TYPE_CHECKING,
    Any,
    Callable,
    Dict,
    Generic,
    Optional,
    Type,
    TypeVar,
)

from pydantic import BaseModel
from pydantic.fields import FieldInfo
from pydantic_core import core_schema

from ninja import Body
from ninja.utils import is_optional_type

try:
    copy_field_info: Callable[[FieldInfo], FieldInfo] = FieldInfo._copy
except AttributeError:
    # Fallback for Pydantic<2.11.0
    copy_field_info = copy.copy


class ModelToDict(dict):
    _wrapped_model: Any = None
    _wrapped_model_dump_params: Dict[str, Any] = {}

    @classmethod
    def __get_pydantic_core_schema__(cls, _source: Any, _handler: Any) -> Any:
        return core_schema.no_info_after_validator_function(
            cls._validate,
            cls._wrapped_model.__pydantic_core_schema__,
        )

    @classmethod
    def _validate(cls, input_value: Any) -> Any:
        return input_value.model_dump(**cls._wrapped_model_dump_params)


def create_patch_schema(schema_cls: Type[BaseModel]) -> Type[ModelToDict]:
    values: Dict[str, Any] = {}
    annotations = {}

    for name, field in schema_cls.model_fields.items():
        annotation: Any = field.annotation
        if is_optional_type(annotation):
            continue
        patch_field = copy_field_info(field)
        patch_field.default = None
        patch_field.default_factory = None
        values[name] = patch_field
        annotations[name] = Optional[annotation]
    values["__annotations__"] = annotations
    OptionalSchema = type(f"{schema_cls.__name__}Patch", (schema_cls,), values)

    class OptionalDictSchema(ModelToDict):
        _wrapped_model = OptionalSchema
        _wrapped_model_dump_params = {"exclude_unset": True}

    return OptionalDictSchema


class PatchDictUtil:
    def __getitem__(self, schema_cls: Type[BaseModel]) -> Any:
        new_cls = create_patch_schema(schema_cls)
        return Body[new_cls]  # type: ignore


if TYPE_CHECKING:  # pragma: nocover
    T = TypeVar("T")

    class PatchDict(Dict[Any, Any], Generic[T]):
        pass

else:
    PatchDict = PatchDictUtil()
