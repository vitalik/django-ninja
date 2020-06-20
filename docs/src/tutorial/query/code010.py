import datetime
from ninja import Schema, Query


class Filters(Schema):
    limit: int = 100
    offset: int = None
    query: str = None


@api.get("/filter")
def events(request, filters: Filters = Query(...)):
    return {"filters": filters.dict()}
