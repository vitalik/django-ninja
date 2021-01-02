import json
from typing import List
from django.http import QueryDict, HttpRequest


class Parser:
    "Default json parser"

    def parse_body(self, request: HttpRequest):
        return json.loads(request.body)

    def parse_querydict(
        self, data: QueryDict, list_fields: List[str], request: HttpRequest
    ):
        result = {}
        for key in data.keys():
            if key in list_fields:
                result[key] = data.getlist(key)
            else:
                result[key] = data[key]
        return result
