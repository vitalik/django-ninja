from ninja import Form, Schema
from pydantic import FieldValidationInfo
from pydantic.fields import FieldInfo
from pydantic_core import core_schema
from typing import Any, Generic, TypeVar

PydanticField = TypeVar("PydanticField")


class EmptyStrToDefault(Generic[PydanticField]):
    @classmethod
    def __get_pydantic_core_schema__(cls, source, handler):
        return core_schema.field_plain_validator_function(cls.validate)

    # @classmethod
    # def __get_pydantic_json_schema__(cls, schema, handler):
    #     return {"type": "object"}

    @classmethod
    def validate(cls, value: Any, info: FieldValidationInfo) -> Any:
        if value == "":
            return info.default
        return value

    # @classmethod
    # def __get_validators__(cls):
    #     yield cls.validate

    # @classmethod
    # def validate(cls, value: PydanticField, field: FieldInfo) -> PydanticField:
    #     if value == "":
    #         return field.default
    #     return value


class Item(Schema):
    name: str
    description: str = None
    price: EmptyStrToDefault[float] = 0.0
    quantity: EmptyStrToDefault[int] = 0
    in_stock: EmptyStrToDefault[bool] = True


@api.post("/items-blank-default")
def update(request, item: Item = Form(...)):
    return item.dict()
