from functools import wraps
from typing import Any, Optional, Tuple

from django.core.cache import caches
from django.core.cache.backends.base import BaseCache
from django.core.handlers.wsgi import WSGIRequest
from django.http.response import HttpResponse, HttpResponseBase
from django.utils.cache import get_cache_key, learn_cache_key, patch_response_headers

from ninja.conf import settings
from ninja.operation import Operation
from ninja.signature import is_async
from ninja.types import DictStrAny, TCallable

HEADER_STATUS_CODES = {200, 304}


class CachePage:
    """Class decorator for caching.

    ```python
    from ninja.cache import cache_page
    @router.get('/ping', response=...)
    @cache_page(timeout=..., cache_alias=..., key_prefix=...)
    def pong(request):
        ...
    ```
    """

    def __init__(
        self,
        timeout: int = settings.DEFAULT_CACHE_TIMEOUT,
        cache_alias: str = "default",
        key_prefix: Optional[str] = None,
    ):
        self.timeout = timeout
        self.cache: BaseCache = caches[cache_alias]
        self.key_prefix = key_prefix
        self.operation: Optional[Operation] = None

    def before(self, request: WSGIRequest, *args: Tuple, **kwargs: DictStrAny) -> Any:
        if request.method != "GET":
            return None

        cache_key = get_cache_key(
            request, self.key_prefix, request.method, cache=self.cache
        )

        result = self.cache.get(cache_key)
        if cache_key is not None and result:
            if isinstance(result, dict):
                _response = HttpResponse(content=result.get("content", b""))
                for header, value in (result.get("headers") or {}).items():
                    _response[header] = value
                return _response
            return result

    def after(
        self, result: Any, request: WSGIRequest, *args: Tuple, **kwargs: DictStrAny
    ) -> Any:
        if not self.operation:
            return result

        response: HttpResponseBase = self.operation._result_to_response(request, result)

        if response.status_code in HEADER_STATUS_CODES:
            patch_response_headers(response, self.timeout)

        if (
            isinstance(response, HttpResponse)
            and not response.streaming
            and response.status_code == 200
        ):
            self.cache.set(
                learn_cache_key(
                    request, response, self.timeout, self.key_prefix, cache=self.cache
                ),
                response,
                timeout=self.timeout,
            )

        return response

    def __call__(self, api_view_func: TCallable) -> TCallable:
        if is_async(api_view_func):

            @wraps(api_view_func)
            async def wrapper(
                request: WSGIRequest, *args: Tuple, **kwargs: DictStrAny
            ) -> Any:
                result = self.before(request, *args, **kwargs)
                if result:
                    return result

                result = await api_view_func(request, *args, **kwargs)

                response = self.after(result, request, *args, **kwargs)

                return response

        else:

            @wraps(api_view_func)
            def wrapper(
                request: WSGIRequest, *args: Tuple, **kwargs: DictStrAny
            ) -> Any:
                result = self.before(request, *args, **kwargs)
                if result:
                    return result

                result = api_view_func(request, *args, **kwargs)

                response = self.after(result, request, *args, **kwargs)

                return response

        wrapper._ninja_contribute_to_operation = self.set_operation  # type: ignore
        return wrapper  # type: ignore

    def set_operation(self, op: Optional[Operation]) -> None:
        self.operation = op

    _ninja_contribute_to_operation = set_operation


cache_page = CachePage
