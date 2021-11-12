@api.get("/items/{item_id}")
def read_item(item_id):
    return {"item_id": item_id}
