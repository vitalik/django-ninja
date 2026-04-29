import json
from typing import Any, Dict, Generic, Type, TypeVar

from ninja.responses import NinjaJSONEncoder

__all__ = ["StreamFormat", "SSE", "JSONL"]


T = TypeVar("T")


def _serialize_item(item: Any) -> str:
    return json.dumps(item, cls=NinjaJSONEncoder)


class _StreamAlias(Generic[T]):
    """Marker created by StreamFormat[ItemType]."""

    def __init__(self, format_cls: Type[Any], item_type: Type[T]) -> None:
        self.format_cls = format_cls
        self.item_type = item_type


class StreamFormat(Generic[T]):
    """Base class for streaming formats. Extensible by users."""

    media_type: str

    def __class_getitem__(cls, item_type: Type[T]) -> "_StreamAlias[T]":
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
    def response_headers(cls) -> Dict[str, str]:
        """Extra headers for the streaming response."""
        return {}


class JSONL(StreamFormat, Generic[T]):
    media_type = "application/jsonl"

    @classmethod
    def format_chunk(cls, data: str) -> str:
        return data + "\n"


class SSE(StreamFormat, Generic[T]):
    media_type = "text/event-stream"

    @classmethod
    def format_chunk(cls, data: str) -> str:
        return f"data: {data}\n\n"

    @classmethod
    def response_headers(cls) -> Dict[str, str]:
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
