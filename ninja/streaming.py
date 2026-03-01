import json
from typing import Any

from ninja.responses import NinjaJSONEncoder

__all__ = ["StreamFormat", "SSE", "JSONL"]


def _serialize_item(item: Any) -> str:
    return json.dumps(item, cls=NinjaJSONEncoder)


class _StreamAlias:
    """Marker created by StreamFormat[ItemType]."""

    def __init__(self, format_cls: type, item_type: type) -> None:
        self.format_cls = format_cls
        self.item_type = item_type


class StreamFormat:
    """Base class for streaming formats. Extensible by users."""

    media_type: str

    def __class_getitem__(cls, item_type: type) -> _StreamAlias:
        return _StreamAlias(cls, item_type)

    @classmethod
    def format_chunk(cls, data: str) -> str:
        """Format a serialized JSON string for this stream."""
        raise NotImplementedError  # pragma: no cover

    @classmethod
    def openapi_content_schema(cls, item_schema: dict) -> dict:
        """Generate OpenAPI content dict for this format."""
        return {cls.media_type: {"schema": item_schema}}

    @classmethod
    def response_headers(cls) -> dict[str, str]:
        """Extra headers for the streaming response."""
        return {}


class JSONL(StreamFormat):
    media_type = "application/jsonl"

    @classmethod
    def format_chunk(cls, data: str) -> str:
        return data + "\n"


class SSE(StreamFormat):
    media_type = "text/event-stream"

    @classmethod
    def format_chunk(cls, data: str) -> str:
        return f"data: {data}\n\n"

    @classmethod
    def response_headers(cls) -> dict[str, str]:
        return {"Cache-Control": "no-cache", "X-Accel-Buffering": "no"}

    @classmethod
    def openapi_content_schema(cls, item_schema: dict) -> dict:
        return {
            cls.media_type: {
                "schema": {
                    "type": "object",
                    "properties": {
                        "data": item_schema,
                    },
                    "description": "SSE event with JSON data payload",
                }
            }
        }
