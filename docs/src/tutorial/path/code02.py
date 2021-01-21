@api.get("/items/{item_id}")
def read_item(request, item_id: int):
    return {"item_id": item_id}
