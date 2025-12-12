from typing import Optional

from ninja import NinjaAPI, Schema

api = NinjaAPI()


class Item(Schema):
    name: str
    description: Optional[str] = None
    price: float
    quantity: int


@api.post("/items")
def create(request, item: Item):
    return item
