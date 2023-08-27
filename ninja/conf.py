from django.conf import settings as django_settings
from pydantic import BaseModel, Field


class Settings(BaseModel):
    """
    Alter these by modifying the values in Django's settings module (usually
    `settings.py`).

    Attributes:
        NINJA_PAGINATION_CLASS (str):
            The pagination class to use. Defaults to
            `ninja.pagination.Pagination`.
        NINJA_PAGINATION_PAGE_SIZE (int):
            The default page size. Defaults to `100`.
    """

    PAGINATION_CLASS: str = Field(
        "ninja.pagination.LimitOffsetPagination", alias="NINJA_PAGINATION_CLASS"
    )
    PAGINATION_PER_PAGE: int = Field(100, alias="NINJA_PAGINATION_PER_PAGE")

    class Config:
        from_attributes = True


settings = Settings.model_validate(django_settings)

if hasattr(django_settings, "NINJA_DOCS_VIEW"):
    raise Exception(
        "NINJA_DOCS_VIEW is removed. Use NinjaAPI(docs=...) instead"
    )  # pragma: no cover
