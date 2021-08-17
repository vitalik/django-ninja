from django.conf import settings as django_settings
from pydantic import BaseModel, Field


class Settings(BaseModel):
    PAGINATION_CLASS: str = Field(
        "ninja.pagination.LimitOffsetPagination", alias="NINJA_PAGINATION_CLASS"
    )
    PAGINATION_PER_PAGE: int = Field(100, alias="NINJA_PAGINATION_PER_PAGE")

    class Config:
        orm_mode = True


settings = Settings.from_orm(django_settings)
