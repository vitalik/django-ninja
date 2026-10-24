"""Compatibility layer for async streaming responses.

Django 4.2+ supports passing async iterators to StreamingHttpResponse.
On older versions, async generators must be eagerly consumed into a list.

TODO: When dropping Django < 4.2 support:
  1. Remove this module entirely.
  2. In AsyncOperation._async_stream_response (ninja/operation.py),
     pass the async content generator directly to StreamingHttpResponse
     and copy temporal_response headers lazily inside the generator:

         async def content_iter():
             async for chunk in content_gen:
                 yield chunk
             for key, value in temporal_response.items():
                 if key.lower() != "content-type":
                     response[key] = value
             for cookie_name, cookie in temporal_response.cookies.items():
                 response.cookies[cookie_name] = cookie

         response = StreamingHttpResponse(
             content_iter(), content_type=..., status=...,
         )
"""

from typing import Any, Dict

import django
from django.http import HttpResponse, StreamingHttpResponse

ASYNC_STREAMING = django.VERSION >= (4, 2)


class _AsyncOnly:
    """Wrap an async iterator so that it is exposed as *only* async.

    Django's ``StreamingHttpResponse._set_streaming_content`` decides
    whether the content is synchronous or asynchronous by trying
    ``iter(value)`` first and only falling back to ``aiter(value)`` when
    that raises ``TypeError``::

        try:
            self._iterator = iter(value)
            self.is_async = False
        except TypeError:
            self._iterator = aiter(value)
            self.is_async = True

    That detection is unreliable for async iterators: whether ``iter()``
    raises on an async generator depends on the Python version and the
    iterator implementation, and any async iterator that also happens to
    define ``__iter__`` is silently misclassified as synchronous.  A
    misclassified response makes Django's ASGI handler emit
    "StreamingHttpResponse must consume synchronous iterators in order to
    serve them asynchronously" on every request and consume the stream
    through a ``sync_to_async(list)`` fallback, defeating streaming.

    This wrapper exposes ``__aiter__`` only - it deliberately has no
    ``__iter__`` - so Django always detects the content as asynchronous,
    regardless of the wrapped iterator or the Python version.
    """

    __slots__ = ("_iterator",)

    def __init__(self, iterator: Any) -> None:
        self._iterator = iterator

    def __aiter__(self) -> Any:
        return self._iterator.__aiter__()

    async def aclose(self) -> None:
        """Forward ``aclose()`` to the wrapped iterator, if it has one."""
        aclose = getattr(self._iterator, "aclose", None)
        if aclose is not None:
            await aclose()


def _copy_temporal_headers(
    temporal_response: HttpResponse, response: StreamingHttpResponse
) -> None:
    """Copy headers and cookies from temporal response, skipping Content-Type."""
    for key, value in temporal_response.items():
        if key.lower() != "content-type":
            response[key] = value
    for cookie_name, cookie in temporal_response.cookies.items():
        response.cookies[cookie_name] = cookie


if ASYNC_STREAMING:

    async def create_streaming_response(
        content_gen: Any,
        *,
        content_type: str,
        status: int,
        temporal_response: HttpResponse,
        extra_headers: Dict[str, str],
    ) -> StreamingHttpResponse:
        """Create a StreamingHttpResponse from an async content generator.

        Django 4.2+: passes the async generator directly and copies
        temporal response headers/cookies lazily after the generator is exhausted.
        """

        async def with_lazy_headers() -> Any:
            async for chunk in content_gen:
                yield chunk
            _copy_temporal_headers(temporal_response, response)

        response = StreamingHttpResponse(
            _AsyncOnly(with_lazy_headers()),
            content_type=content_type,
            status=status,
        )
        for key, value in extra_headers.items():
            response[key] = value
        return response

else:

    async def create_streaming_response(
        content_gen: Any,
        *,
        content_type: str,
        status: int,
        temporal_response: HttpResponse,
        extra_headers: Dict[str, str],
    ) -> StreamingHttpResponse:
        """Create a StreamingHttpResponse from an async content generator.

        Django < 4.2: eagerly consumes the async generator into a list
        since StreamingHttpResponse does not support async iterators.
        """
        chunks = []
        async for chunk in content_gen:
            chunks.append(chunk)
        response = StreamingHttpResponse(
            iter(chunks),
            content_type=content_type,
            status=status,
        )
        _copy_temporal_headers(temporal_response, response)
        for key, value in extra_headers.items():
            response[key] = value
        return response
