import json
from pydantic import BaseModel
from django.http import QueryDict
from ninja.compatibility import get_headers
from ninja.errors import InvalidBodyJson


class ParamModel(BaseModel):
    @classmethod
    def resolve(cls, request, path_params):
        data = cls.get_request_data(request, path_params)
        if data is None:
            return cls()

        varname = getattr(cls, "_single_attr", None)
        if varname:
            data = {varname: data}
        # TODO: I guess if data is not dict - raise an InvalidInput
        return cls(**data)


class QueryModel(ParamModel):
    @classmethod
    def get_request_data(cls, request, path_params):
        return _querydict_to_dict(cls, request.GET)


class PathModel(ParamModel):
    @classmethod
    def get_request_data(cls, request, path_params):
        return path_params


class HeaderModel(ParamModel):
    @classmethod
    def get_request_data(cls, request, path_params):
        data = {}
        headers = get_headers(request)
        for name, field in cls.__fields__.items():
            if name in headers:
                data[name] = headers[name]
            elif field.alias in headers:
                data[field.alias] = headers[field.alias]
        return data


class CookieModel(ParamModel):
    @classmethod
    def get_request_data(cls, request, path_params):
        return request.COOKIES


class BodyModel(ParamModel):
    @classmethod
    def get_request_data(cls, request, path_params):
        if request.body:
            try:
                # TODO: maybe better to cache data on request instance if multiple bodies parsing same large body
                return json.loads(request.body)
            except Exception as e:
                raise InvalidBodyJson(e)


class FormModel(ParamModel):
    @classmethod
    def get_request_data(cls, request, path_params):
        return _querydict_to_dict(cls, request.POST)


def _querydict_to_dict(cls, data: QueryDict):
    list_fields = getattr(cls, "_collection_fields", [])
    result = {}
    for key in data.keys():
        if key in list_fields:
            result[key] = data.getlist(key)
        else:
            result[key] = data[key]
    return result
