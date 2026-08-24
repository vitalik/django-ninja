from ninja import NinjaAPI, Schema

api = NinjaAPI()


class Item(Schema):
    name: str
    description: str = None
    price: float
    quantity: int


@api.put("/items/{item_id}")
def update(request, item_id: int, item: Item):
    return {"item_id": item_id, "item": item.dict()}
