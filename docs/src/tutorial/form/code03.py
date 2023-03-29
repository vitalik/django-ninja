from ninja import Form, Schema
from pydantic.fields import ModelField
from typing import Generic, TypeVar

PydanticField = TypeVar("PydanticField")


class EmptyStrToDefault(Generic[PydanticField]):
    @classmethod
    def __get_validators__(cls):
        yield cls.validate

    @classmethod
    def validate(cls, value: PydanticField, field: ModelField) -> PydanticField:
        if value == "":
            return field.default
        return value


class Item(Schema):
    name: str
    description: str = None
    price: EmptyStrToDefault[float] = 0.0
    quantity: EmptyStrToDefault[int] = 0
    in_stock: EmptyStrToDefault[bool] = True


@api.post("/items-blank-default")
def update(request, item: Item=Form(...)):
    return item.dict()
