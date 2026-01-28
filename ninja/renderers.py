import itertools
import json
from typing import Any, List, Mapping, Type

from django.http import HttpRequest
from django.http.request import parse_accept_header

from ninja.responses import NinjaJSONEncoder

__all__ = ["BaseRenderer", "JSONRenderer"]


class BaseRenderer:
    media_type: str
    charset: str = "utf-8"

    def get_media_type(self, request: HttpRequest) -> str:
        return self.media_type

    def render(self, request: HttpRequest, data: Any, *, response_status: int) -> Any:
        raise NotImplementedError("Please implement .render() method")


class BaseDynamicRenderer(BaseRenderer):
    media_types: List[str]

    def get_media_type(self, request: HttpRequest) -> str:
        accepted_media_types = parse_accept_header(request.headers.get("accept", "*/*"))
        media_type_gen = (
            media_type
            for media_type, accepted_type in itertools.product(
                self.media_types, accepted_media_types
            )
            if accepted_type.match(media_type)
        )

        return next(media_type_gen, self.media_type)


class JSONRenderer(BaseRenderer):
    media_type = "application/json"
    encoder_class: Type[json.JSONEncoder] = NinjaJSONEncoder
    json_dumps_params: Mapping[str, Any] = {}

    def render(self, request: HttpRequest, data: Any, *, response_status: int) -> Any:
        return json.dumps(data, cls=self.encoder_class, **self.json_dumps_params)
