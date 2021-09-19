from ninja import Form, Schema


class Item(Schema):
    name: str
    description: str = None
    price: float
    quantity: int


@api.post("/items")
def create(request, item: Item = Form(...)):
    return item
