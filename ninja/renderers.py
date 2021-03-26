import json
from typing import Any, Mapping, Optional, Type

from django.http import HttpRequest

from ninja.responses import NinjaJSONEncoder

__all__ = ["BaseRenderer", "JSONRenderer"]


class BaseRenderer:
    media_type: Optional[str] = None
    charset: str = "utf-8"

    def render(self, request: HttpRequest, data: Any, *, response_status: int) -> Any:
        raise NotImplementedError("Please implement .render() method")


class JSONRenderer(BaseRenderer):
    media_type = "application/json"
    encoder_class: Type[json.JSONEncoder] = NinjaJSONEncoder
    json_dumps_params: Mapping[str, Any] = {}

    def render(self, request: HttpRequest, data: Any, *, response_status: int) -> Any:
        return json.dumps(data, cls=self.encoder_class, **self.json_dumps_params)
