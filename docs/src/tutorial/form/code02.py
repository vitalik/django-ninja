from ninja import Form, Schema


class Item(Schema):
    name: str
    description: str = None
    price: float
    quantity: int


@api.post("/items/{item_id}")
def update(request, item_id: int, q: str, item: Item=Form(...)):
    return {"item_id": item_id, "item": item.dict(), "q": q}
