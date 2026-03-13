from ninja import Form, NinjaAPI, Schema

api = NinjaAPI()


class Item(Schema):
    name: str
    description: str = None
    price: float
    quantity: int


@api.post("/items")
def create(request, item: Form[Item]):
    return item
