import json
from typing import Any
from django.http import HttpRequest
from ninja.responses import NinjaJSONEncoder


class BaseRenderer:
    media_type = None
    charset = "utf-8"

    def render(self, request: HttpRequest, data: Any, *, response_status: int):
        raise NotImplementedError("Please implement .render() method")


class JSONRenderer(BaseRenderer):
    media_type = "application/json"
    encoder_class = NinjaJSONEncoder
    json_dumps_params = {}

    def render(self, request: HttpRequest, data: Any, *, response_status: int):
        return json.dumps(data, cls=self.encoder_class, **self.json_dumps_params)
