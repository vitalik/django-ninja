import json
from collections.abc import Mapping
from typing import Any, Optional

from django.http import HttpRequest
from pydantic_core import to_json

from ninja.responses import NinjaJSONEncoder

__all__ = ["BaseRenderer", "JSONRenderer", "PydanticJSONRenderer"]


class BaseRenderer:
    media_type: Optional[str] = None
    charset: str = "utf-8"

    def render(self, request: HttpRequest, data: Any, *, response_status: int) -> Any:
        raise NotImplementedError("Please implement .render() method")


class JSONRenderer(BaseRenderer):
    media_type = "application/json"
    encoder_class: type[json.JSONEncoder] = NinjaJSONEncoder
    json_dumps_params: Mapping[str, Any] = {}

    def render(self, request: HttpRequest, data: Any, *, response_status: int) -> Any:
        return json.dumps(data, cls=self.encoder_class, **self.json_dumps_params)


class PydanticJSONRenderer(JSONRenderer):
    """
    Serializes with pydantic's JSON serializer instead of `json.dumps`.

    Responses with a `response=` schema are written straight to JSON bytes,
    skipping the intermediate `model_dump()` to Python objects.
    `json_dumps_params` is not used.
    """

    def render(self, request: HttpRequest, data: Any, *, response_status: int) -> Any:
        return to_json(data, fallback=self.fallback)

    def fallback(self, value: Any) -> Any:
        "Converts values pydantic can't serialize itself (lazy strings etc.)"
        return self.encoder_class().default(value)
