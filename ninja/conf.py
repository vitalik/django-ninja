from django.conf import settings as django_settings
from pydantic import BaseModel, Field


class Settings(BaseModel):
    PAGINATION_CLASS: str = Field(
        "ninja.pagination.LimitOffsetPagination", alias="NINJA_PAGINATION_CLASS"
    )
    PAGINATION_PER_PAGE: int = Field(100, alias="NINJA_PAGINATION_PER_PAGE")
    DEFAULT_CACHE_TIMEOUT: int = Field(3600, alias="NINJA_DEFAULT_CACHE_TIMEOUT")

    class Config:
        orm_mode = True


settings = Settings.from_orm(django_settings)
