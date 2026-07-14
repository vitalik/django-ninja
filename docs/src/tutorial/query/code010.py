from typing import List

from pydantic import Field

from ninja import NinjaAPI, Query, Schema

api = NinjaAPI()


class Filters(Schema):
    limit: int = 100
    offset: int = None
    query: str = None
    category__in: List[str] = Field(None, alias="categories")


@api.get("/filter")
def events(request, filters: Query[Filters]):
    return {"filters": filters.dict()}
