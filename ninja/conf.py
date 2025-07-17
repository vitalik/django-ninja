from math import inf
from typing import Dict, Optional, Set

from django.conf import settings as django_settings
from pydantic import BaseModel, Field


class Settings(BaseModel):
    # Pagination
    PAGINATION_CLASS: str = Field(
        "ninja.pagination.LimitOffsetPagination", alias="NINJA_PAGINATION_CLASS"
    )
    PAGINATION_PER_PAGE: int = Field(100, alias="NINJA_PAGINATION_PER_PAGE")
    PAGINATION_MAX_PER_PAGE_SIZE: int = Field(100, alias="NINJA_MAX_PER_PAGE_SIZE")
    PAGINATION_MAX_LIMIT: int = Field(inf, alias="NINJA_PAGINATION_MAX_LIMIT")  # type: ignore

    # Throttling
    NUM_PROXIES: Optional[int] = Field(None, alias="NINJA_NUM_PROXIES")
    DEFAULT_THROTTLE_RATES: Dict[str, Optional[str]] = Field(
        {
            "auth": "10000/day",
            "user": "10000/day",
            "anon": "1000/day",
        },
        alias="NINJA_DEFAULT_THROTTLE_RATES",
    )

    FIX_REQUEST_FILES_METHODS: Set[str] = Field(
        {"PUT", "PATCH", "DELETE"}, alias="NINJA_FIX_REQUEST_FILES_METHODS"
    )

    class Config:
        from_attributes = True


settings = Settings.model_validate(django_settings)

if hasattr(django_settings, "NINJA_DOCS_VIEW"):
    raise Exception(
        "NINJA_DOCS_VIEW is removed. Use NinjaAPI(docs=...) instead"
    )  # pragma: no cover
