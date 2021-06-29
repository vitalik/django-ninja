from typing import TypeVar, Generic, Optional, List
import pydantic
from pydantic.generics import GenericModel

GenericResultsType = TypeVar("GenericResultsType")


class PaginatedResponseSchema(GenericModel, Generic[GenericResultsType]):
    count: int
    next: Optional[pydantic.AnyHttpUrl]
    previous: Optional[pydantic.AnyHttpUrl]
    results: List[GenericResultsType]
