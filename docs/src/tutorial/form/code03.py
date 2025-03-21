from ninja import Form, Schema
from typing import Annotated, TypeVar
from pydantic import WrapValidator
from pydantic_core import PydanticUseDefault


def _empty_str_to_default(v, handler, info):
    if isinstance(v, str) and v == '':
        raise PydanticUseDefault
    return handler(v)


T = TypeVar('T')
EmptyStrToDefault = Annotated[T, WrapValidator(_empty_str_to_default)]


class Item(Schema):
    name: str
    description: str = None
    price: EmptyStrToDefault[float] = 0.0
    quantity: EmptyStrToDefault[int] = 0
    in_stock: EmptyStrToDefault[bool] = True


@api.post("/items-blank-default")
def update(request, item: Form[Item]):
    return item.dict()
