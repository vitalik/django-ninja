from math import inf

from django.conf import settings as django_settings
from pydantic import BaseModel, Field
from pydantic.json_schema import JsonSchemaMode


class Settings(BaseModel):
    """
    Alter these by modifying the values in Django's settings module (usually
    `settings.py`).

    Attributes:
        NINJA_PAGINATION_CLASS (str):
            The pagination class to use. Defaults to
            `ninja.pagination.LimitOffsetPagination`.
        NINJA_PAGINATION_PER_PAGE (int):
            The default page size. Defaults to `100`.
        NINJA_PAGINATION_MAX_LIMIT (int):
            The maximum number of results per page. Defaults to `inf`.
        NINJA_SCHEMA_GENERATOR_CLASS (str):
            The schema generation class to use. Defaults to
            `ninja.schema.NinjaGenerateJsonSchema`.
        NINJA_SCHEMA_MODE (str):
            The schema mode to use. Defaults to `serialization`.
    """

    PAGINATION_CLASS: str = Field(
        "ninja.pagination.LimitOffsetPagination", alias="NINJA_PAGINATION_CLASS"
    )
    PAGINATION_PER_PAGE: int = Field(100, alias="NINJA_PAGINATION_PER_PAGE")
    PAGINATION_MAX_LIMIT: int = Field(inf, alias="NINJA_PAGINATION_MAX_LIMIT")

    SCHEMA_GENERATOR_CLASS: str = Field(
        "ninja.schema.NinjaGenerateJsonSchema", alias="NINJA_SCHEMA_GENERATOR_CLASS"
    )
    SCHEMA_MODE: JsonSchemaMode = Field(
        "serialization", alias="NINJA_SCHEMA_MODE"
    )

    class Config:
        from_attributes = True


settings = Settings.model_validate(django_settings)

if hasattr(django_settings, "NINJA_DOCS_VIEW"):
    raise Exception(
        "NINJA_DOCS_VIEW is removed. Use NinjaAPI(docs=...) instead"
    )  # pragma: no cover
