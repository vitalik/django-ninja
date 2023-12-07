"""Django Ninja - Fast Django REST framework"""

__version__ = "1.1.0"


from pydantic import Field

from ninja.files import UploadedFile
from ninja.filter_schema import FilterSchema
from ninja.main import NinjaAPI
from ninja.openapi.docs import Redoc, Swagger
from ninja.orm import ModelSchema
from ninja.params import (
    Body,
    BodyEx,
    Cookie,
    CookieEx,
    File,
    FileEx,
    Form,
    FormEx,
    Header,
    HeaderEx,
    P,
    Path,
    PathEx,
    Query,
    QueryEx,
)
from ninja.router import Router
from ninja.schema import Schema

__all__ = [
    "Field",
    "UploadedFile",
    "NinjaAPI",
    "Body",
    "Cookie",
    "File",
    "Form",
    "Header",
    "Path",
    "Query",
    "BodyEx",
    "CookieEx",
    "FileEx",
    "FormEx",
    "HeaderEx",
    "PathEx",
    "QueryEx",
    "Router",
    "P",
    "Schema",
    "ModelSchema",
    "FilterSchema",
    "Swagger",
    "Redoc",
]
