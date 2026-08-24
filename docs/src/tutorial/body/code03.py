from ninja import NinjaAPI, Schema

api = NinjaAPI()


class Item(Schema):
    name: str
    description: str = None
    price: float
    quantity: int


@api.post("/items/{item_id}")
def update(request, item_id: int, item: Item, q: str):
    return {"item_id": item_id, "item": item.dict(), "q": q}
