from functools import wraps
from typing import Any, Callable, Optional, Tuple

from django.core.cache import caches
from django.core.cache.backends.base import BaseCache
from django.core.handlers.wsgi import WSGIRequest
from django.http.response import HttpResponse, HttpResponseBase
from django.utils.cache import get_cache_key, learn_cache_key, patch_response_headers

from ninja.conf import settings
from ninja.operation import Operation
from ninja.signature.utils import is_async
from ninja.types import DictStrAny

HEADER_STATUS_CODES = {200, 304}


def cache_page(
    timeout: int = settings.DEFAULT_CACHE_TIMEOUT,
    cache_alias: str = "default",
    key_prefix: Optional[str] = None,
) -> Callable:
    """Decorator for caching.

    ```python
    @router.get('/ping', response=...)
    @cache_page(timeout=..., cache_alias=..., key_prefix=...)
    def pong(request):
        ...
    ```
    """
    operation: Optional[Operation] = None
    cache: BaseCache = caches[cache_alias]

    def set_operation(op: Operation) -> None:
        nonlocal operation
        operation = op

    def _decorator(api_view_func: Callable) -> Callable:
        is_async_view = is_async(api_view_func)

        @wraps(api_view_func)
        def wrapper(request: WSGIRequest, *args: Tuple, **kwargs: DictStrAny) -> Any:
            if request.method != "GET":
                return api_view_func(request, *args, **kwargs)

            cache_key = get_cache_key(request, key_prefix, request.method, cache=cache)

            result = cache.get(cache_key)
            if cache_key is not None and result:
                if isinstance(result, dict):
                    _response = HttpResponse(content=result.pop("content", b""))
                    for header, value in (result.get("headers") or {}).items():
                        _response[header] = value
                    return _response
                return result
            if is_async_view:  # pragma: no cover

                async def tmp() -> Any:
                    return await api_view_func(request, *args, **kwargs)

                result = tmp()
            else:
                result = api_view_func(request, *args, **kwargs)
            if not operation:  # pragma: no cover
                return result

            response: HttpResponseBase = operation._result_to_response(request, result)

            if response.status_code in HEADER_STATUS_CODES:
                patch_response_headers(response, timeout)

            if (
                isinstance(response, HttpResponse)
                and not response.streaming
                and response.status_code == 200
            ):
                cache.set(
                    learn_cache_key(
                        request, response, timeout, key_prefix, cache=cache
                    ),
                    response,
                    timeout=timeout,
                )

            return response

        wrapper._ninja_contribute_to_operation = set_operation  # type: ignore
        return wrapper

    return _decorator
