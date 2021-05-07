import datetime
from typing import List

from pydantic import Field

from ninja import Query, Schema


class Filters(Schema):
    limit: int = 100
    offset: int = None
    query: str = None
    category__in: List[str] = Field(None, alias="categories")


@api.get("/filter")
def events(request, filters: Filters = Query(...)):
    return {"filters": filters.dict()}
