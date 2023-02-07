from abc import ABC, abstractmethod
from collections import defaultdict
from typing import TYPE_CHECKING, Any, List, Optional, Tuple, Type, TypeVar

from django.conf import settings
from django.http import HttpRequest
from pydantic import BaseModel

from ninja.compatibility import get_headers
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
    _param_source = None

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
        return cls(**data)

    @classmethod
    def _map_data_paths(cls, data: DictStrAny) -> DictStrAny:
        flatten_map = getattr(cls, "_flatten_map", None)
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
        list_fields = getattr(cls, "_collection_fields", [])
        return api.parser.parse_querydict(request.GET, list_fields, request)


class PathModel(ParamModel):
    @classmethod
    def get_request_data(
        cls, request: HttpRequest, api: "NinjaAPI", path_params: DictStrAny
    ) -> Optional[DictStrAny]:
        return path_params


class HeaderModel(ParamModel):
    _flatten_map: DictStrAny

    @classmethod
    def get_request_data(
        cls, request: HttpRequest, api: "NinjaAPI", path_params: DictStrAny
    ) -> Optional[DictStrAny]:
        data = {}
        headers = get_headers(request)
        for name in cls._flatten_map:
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
    _single_attr: str

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
                raise HttpError(400, msg)

            varname = getattr(cls, "_single_attr", None)
            if varname:
                data = {varname: data}
            return data

        return None


class FormModel(ParamModel):
    @classmethod
    def get_request_data(
        cls, request: HttpRequest, api: "NinjaAPI", path_params: DictStrAny
    ) -> Optional[DictStrAny]:
        list_fields = getattr(cls, "_collection_fields", [])
        return api.parser.parse_querydict(request.POST, list_fields, request)


class FileModel(ParamModel):
    @classmethod
    def get_request_data(
        cls, request: HttpRequest, api: "NinjaAPI", path_params: DictStrAny
    ) -> Optional[DictStrAny]:
        list_fields = getattr(cls, "_collection_fields", [])
        return api.parser.parse_querydict(request.FILES, list_fields, request)


class _HttpRequest(HttpRequest):
    body: bytes = b""


class _MultiPartBodyModel(BodyModel):
    _body_params: DictStrAny

    @classmethod
    def get_request_data(
        cls, request: HttpRequest, api: "NinjaAPI", path_params: DictStrAny
    ) -> Optional[DictStrAny]:
        req = _HttpRequest()
        get_request_data = super(_MultiPartBodyModel, cls).get_request_data
        results: DictStrAny = {}
        for name, annotation in cls._body_params.items():
            if name in request.POST:
                data = request.POST[name]
                if annotation == str and data[0] != '"' and data[-1] != '"':
                    data = f'"{data}"'
                req.body = data.encode()
                results[name] = get_request_data(req, api, path_params)
        return results
