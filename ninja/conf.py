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
        NINJA_DOCS_VIEW ("swagger"|"redoc"):
            The view to use for the documentation. Defaults to `swagger`, but
            change to `redoc` to use alternative
            [Redoc](https://github.com/Redocly/redoc) automatic documentation.
    """

    PAGINATION_CLASS: str = Field(
        "ninja.pagination.LimitOffsetPagination", alias="NINJA_PAGINATION_CLASS"
    )
    PAGINATION_PER_PAGE: int = Field(100, alias="NINJA_PAGINATION_PER_PAGE")
    DOCS_VIEW: str = Field("swagger", alias="NINJA_DOCS_VIEW")

    class Config:
        orm_mode = True


settings = Settings.from_orm(django_settings)
