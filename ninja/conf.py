from math import inf
from typing import Any, Dict, Optional, Set, Tuple

from django.conf import settings as django_settings
from django.dispatch import receiver
from django.test.signals import setting_changed
from pydantic import BaseModel, ConfigDict, Field


class Settings(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    # Pagination
    PAGINATION_CLASS: str = Field(
        "ninja.pagination.LimitOffsetPagination", alias="NINJA_PAGINATION_CLASS"
    )
    PAGINATION_DEFAULT_ORDERING: Tuple[str, ...] = Field(
        ("-pk",), alias="NINJA_PAGINATION_DEFAULT_ORDERING"
    )
    PAGINATION_MAX_OFFSET: int = Field(100, alias="NINJA_PAGINATION_MAX_OFFSET")
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


settings = Settings.model_validate(django_settings)


@receiver(setting_changed)
def reload_ninja_settings(*args: Any, setting: str, **kwargs: Any) -> None:
    if not setting.startswith("NINJA_"):
        return

    updated_settings = Settings.model_validate(django_settings)
    for field_name in Settings.model_fields:
        setattr(settings, field_name, getattr(updated_settings, field_name))


if hasattr(django_settings, "NINJA_DOCS_VIEW"):
    raise Exception(
        "NINJA_DOCS_VIEW is removed. Use NinjaAPI(docs=...) instead"
    )  # pragma: no cover
