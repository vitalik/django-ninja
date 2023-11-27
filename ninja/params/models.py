from abc import ABC, abstractmethod
from collections import defaultdict
from typing import TYPE_CHECKING, Any, Dict, List, Optional, Tuple, Type, TypeVar

from django.conf import settings
from django.http import HttpRequest
from pydantic import BaseModel
from pydantic.fields import FieldInfo

from ninja.errors import HttpError
from ninja.types import DictStrAny

if TYPE_CHECKING:
    from ninja import NinjaAPI  # pragma: no cover

__all__ = [
    "ParamModel",
    "QueryModel",
    "PathModel",
    "HeaderModel",
    "CookieModel",
    "BodyModel",
    "FormModel",
    "FileModel",
]

TModel = TypeVar("TModel", bound="ParamModel")
TModels = List[TModel]


def NestedDict() -> DictStrAny:
    return defaultdict(NestedDict)


class ParamModel(BaseModel, ABC):
    __ninja_param_source__ = None

    @classmethod
    @abstractmethod
    def get_request_data(
        cls, request: HttpRequest, api: "NinjaAPI", path_params: DictStrAny
    ) -> Optional[DictStrAny]:
        pass  # pragma: no cover

    @classmethod
    def resolve(
        cls: Type[TModel],
        request: HttpRequest,
        api: "NinjaAPI",
        path_params: DictStrAny,
    ) -> TModel:
        data = cls.get_request_data(request, api, path_params)
        if data is None:
            return cls()

        data = cls._map_data_paths(data)
        return cls.model_validate(data, context={"request": request})

    @classmethod
    def _map_data_paths(cls, data: DictStrAny) -> DictStrAny:
        flatten_map = getattr(cls, "__ninja_flatten_map__", None)
        if not flatten_map:
            return data

        mapped_data: DictStrAny = NestedDict()
        for k in flatten_map:
            if k in data:
                cls._map_data_path(mapped_data, data[k], flatten_map[k])
            else:
                cls._map_data_path(mapped_data, None, flatten_map[k])

        return mapped_data

    @classmethod
    def _map_data_path(cls, data: DictStrAny, value: Any, path: Tuple) -> None:
        if len(path) == 1:
            if value is not None:
                data[path[0]] = value
        else:
            cls._map_data_path(data[path[0]], value, path[1:])


class QueryModel(ParamModel):
    @classmethod
    def get_request_data(
        cls, request: HttpRequest, api: "NinjaAPI", path_params: DictStrAny
    ) -> Optional[DictStrAny]:
        list_fields = getattr(cls, "__ninja_collection_fields__", [])
        return api.parser.parse_querydict(request.GET, list_fields, request)


class PathModel(ParamModel):
    @classmethod
    def get_request_data(
        cls, request: HttpRequest, api: "NinjaAPI", path_params: DictStrAny
    ) -> Optional[DictStrAny]:
        return path_params


class HeaderModel(ParamModel):
    __ninja_flatten_map__: DictStrAny

    @classmethod
    def get_request_data(
        cls, request: HttpRequest, api: "NinjaAPI", path_params: DictStrAny
    ) -> Optional[DictStrAny]:
        data = {}
        headers = request.headers
        for name in cls.__ninja_flatten_map__:
            if name in headers:
                data[name] = headers[name]
        return data


class CookieModel(ParamModel):
    @classmethod
    def get_request_data(
        cls, request: HttpRequest, api: "NinjaAPI", path_params: DictStrAny
    ) -> Optional[DictStrAny]:
        return request.COOKIES


class BodyModel(ParamModel):
    __read_from_single_attr__: str

    @classmethod
    def get_request_data(
        cls, request: HttpRequest, api: "NinjaAPI", path_params: DictStrAny
    ) -> Optional[DictStrAny]:
        if request.body:
            try:
                data = api.parser.parse_body(request)
            except Exception as e:
                msg = "Cannot parse request body"
                if settings.DEBUG:
                    msg += f" ({e})"
                raise HttpError(400, msg) from e

            varname = getattr(cls, "__read_from_single_attr__", None)
            if varname:
                data = {varname: data}
            return data

        return None


class FormModel(ParamModel):
    @classmethod
    def get_request_data(
        cls, request: HttpRequest, api: "NinjaAPI", path_params: DictStrAny
    ) -> Optional[DictStrAny]:
        list_fields = getattr(cls, "__ninja_collection_fields__", [])
        return api.parser.parse_querydict(request.POST, list_fields, request)


class FileModel(ParamModel):
    @classmethod
    def get_request_data(
        cls, request: HttpRequest, api: "NinjaAPI", path_params: DictStrAny
    ) -> Optional[DictStrAny]:
        list_fields = getattr(cls, "__ninja_collection_fields__", [])
        return api.parser.parse_querydict(request.FILES, list_fields, request)


class _HttpRequest(HttpRequest):
    body: bytes = b""


class _MultiPartBodyModel(BodyModel):
    __ninja_body_params__: DictStrAny

    @classmethod
    def get_request_data(
        cls, request: HttpRequest, api: "NinjaAPI", path_params: DictStrAny
    ) -> Optional[DictStrAny]:
        req = _HttpRequest()
        get_request_data = super().get_request_data
        results: DictStrAny = {}
        for name, annotation in cls.__ninja_body_params__.items():
            if name in request.POST:
                data = request.POST[name]
                if annotation is str and data[0] != '"' and data[-1] != '"':
                    data = f'"{data}"'
                req.body = data.encode()
                results[name] = get_request_data(req, api, path_params)
        return results


class Param(FieldInfo):
    def __init__(
        self,
        default: Any,
        *,
        alias: Optional[str] = None,
        title: Optional[str] = None,
        description: Optional[str] = None,
        gt: Optional[float] = None,
        ge: Optional[float] = None,
        lt: Optional[float] = None,
        le: Optional[float] = None,
        min_length: Optional[int] = None,
        max_length: Optional[int] = None,
        example: Optional[Any] = None,
        examples: Optional[Dict[str, Any]] = None,
        deprecated: Optional[bool] = None,
        include_in_schema: Optional[bool] = True,
        # param_name: str = None,
        # param_type: Any = None,
        **extra: Any,
    ):
        self.deprecated = deprecated
        # self.param_name: str = None
        # self.param_type: Any = None
        self.model_field: Optional[FieldInfo] = None
        json_schema_extra = {}
        if example:
            json_schema_extra["example"] = example
        if examples:
            json_schema_extra["examples"] = examples
        if deprecated:
            json_schema_extra["deprecated"] = deprecated
        if not include_in_schema:
            json_schema_extra["include_in_schema"] = include_in_schema
        if alias and not extra.get("validation_alias"):
            extra["validation_alias"] = alias
        if alias and not extra.get("serialization_alias"):
            extra["serialization_alias"] = alias

        super().__init__(
            default=default,
            alias=alias,
            title=title,
            description=description,
            gt=gt,
            ge=ge,
            lt=lt,
            le=le,
            min_length=min_length,
            max_length=max_length,
            json_schema_extra=json_schema_extra,
            **extra,
        )

    @classmethod
    def _param_source(cls) -> str:
        "Openapi param.in value or body type"
        return cls.__name__.lower()


class Path(Param):
    _model = PathModel


class Query(Param):
    _model = QueryModel


class Header(Param):
    _model = HeaderModel


class Cookie(Param):
    _model = CookieModel


class Body(Param):
    _model = BodyModel


class Form(Param):
    _model = FormModel


class File(Param):
    _model = FileModel


class _MultiPartBody(Param):
    _model = _MultiPartBodyModel

    @classmethod
    def _param_source(cls) -> str:
        return "body"
