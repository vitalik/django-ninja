import json
from typing import Any, Mapping, Optional, Type

from django.http import HttpRequest
from pydantic import BaseModel

from ninja.responses import NinjaJSONEncoder

__all__ = ["BaseRenderer", "JSONRenderer"]


class BaseRenderer:
    media_type: Optional[str] = None
    charset: str = "utf-8"

    def render(self, request: HttpRequest, data: Any, *, response_status: int) -> Any:
        raise NotImplementedError("Please implement .render() method")

    def pydantic_to_dict(
        self,
        data: BaseModel,
        request: HttpRequest,
        *,
        by_alias: bool = False,
        exclude_unset: bool = False,
        exclude_defaults: bool = False,
        exclude_none: bool = False,
    ) -> dict:
        return data.dict(
            by_alias=by_alias,
            exclude_unset=exclude_unset,
            exclude_defaults=exclude_defaults,
            exclude_none=exclude_none,
        )


class JSONRenderer(BaseRenderer):
    media_type = "application/json"
    encoder_class: Type[json.JSONEncoder] = NinjaJSONEncoder
    json_dumps_params: Mapping[str, Any] = {}

    def render(self, request: HttpRequest, data: Any, *, response_status: int) -> Any:
        return json.dumps(data, cls=self.encoder_class, **self.json_dumps_params)
