"""Django Ninja - Fast Django REST framework"""

__version__ = "0.10.0"

from ninja.main import NinjaAPI
from ninja.params import Query, Path, Header, Cookie, Body, Form, File
from ninja.router import Router
from ninja.schema import Schema
from ninja.files import UploadedFile
from pydantic import Field
