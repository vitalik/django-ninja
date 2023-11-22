from typing import Optional
from ninja import Schema


class Item(Schema):
    name: str
    description: Optional[str] = None
    price: float
    quantity: int


@api.post("/items")
def create(request, item: Item):
    return item
