import json
from typing import List, cast

from django.http import HttpRequest
from django.utils.datastructures import MultiValueDict

from ninja.types import DictStrAny

__all__ = ["Parser"]


class Parser:
    "Default json parser"

    def parse_body(self, request: HttpRequest) -> DictStrAny:
        return cast(DictStrAny, json.loads(request.body))

    def parse_querydict(
        self, data: MultiValueDict, list_fields: List[str], request: HttpRequest
    ) -> DictStrAny:
        result: DictStrAny = {}
        for key in data.keys():
            if key in list_fields:
                result[key] = data.getlist(key)
            else:
                result[key] = data[key]
        return result
