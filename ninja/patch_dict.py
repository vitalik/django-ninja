from typing import TYPE_CHECKING, Any, Dict, Optional, Type

from pydantic_core import core_schema
from typing_extensions import Annotated

from ninja import Body
from ninja.utils import is_optional_type


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


def create_patch_schema(schema_cls: Type[Any]) -> Type[ModelToDict]:
    values, annotations = {}, {}
    for f in schema_cls.__fields__.keys():
        t = schema_cls.__annotations__[f]
        if not is_optional_type(t):
            values[f] = getattr(schema_cls, f, None)
            annotations[f] = Optional[t]
    values["__annotations__"] = annotations
    OptionalSchema = type(f"{schema_cls.__name__}Patch", (schema_cls,), values)

    class OptionalDictSchema(ModelToDict):
        _wrapped_model = OptionalSchema
        _wrapped_model_dump_params = {"exclude_unset": True}

    return OptionalDictSchema


class PatchDictUtil:
    def __getitem__(self, schema_cls: Any) -> Any:
        new_cls = create_patch_schema(schema_cls)
        return Body[new_cls]  # type: ignore


if TYPE_CHECKING:  # pragma: nocover
    PatchDict = Annotated[dict, "<PatchDict>"]
else:
    PatchDict = PatchDictUtil()
