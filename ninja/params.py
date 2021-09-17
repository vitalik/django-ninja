from typing import Any, Optional

from pydantic.fields import FieldInfo, ModelField

from ninja import params_models

__all__ = ["Param", "Path", "Query", "Header", "Cookie", "Body", "Form", "File"]


class Param(FieldInfo):
    def __init__(
        self,
        default: Any,
        *,
        alias: str = None,
        title: str = None,
        description: str = None,
        gt: float = None,
        ge: float = None,
        lt: float = None,
        le: float = None,
        min_length: int = None,
        max_length: int = None,
        regex: str = None,
        deprecated: bool = None,
        # param_name: str = None,
        # param_type: Any = None,
        **extra: Any,
    ):
        self.deprecated = deprecated
        # self.param_name: str = None
        # self.param_type: Any = None
        self.model_field: Optional[ModelField] = None
        super().__init__(
            default,
            alias=alias,
            title=title,
            description=description,
            gt=gt,
            ge=ge,
            lt=lt,
            le=le,
            min_length=min_length,
            max_length=max_length,
            regex=regex,
            **extra,
        )

    @classmethod
    def _param_source(cls) -> str:
        "Openapi param.in value or body type"
        return cls.__name__.lower()


class Path(Param):
    _model = params_models.PathModel


class Query(Param):
    _model = params_models.QueryModel


class Header(Param):
    _model = params_models.HeaderModel


class Cookie(Param):
    _model = params_models.CookieModel


class Body(Param):
    _model = params_models.BodyModel


class Form(Param):
    _model = params_models.FormModel


class File(Param):
    _model = params_models.FileModel


class _MultiPartBody(Param):
    _model = params_models._MultiPartBodyModel
    _param_source = Body._param_source
