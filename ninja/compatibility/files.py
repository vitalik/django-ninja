from typing import Any, List

from asgiref.sync import iscoroutinefunction, sync_to_async
from django.conf import settings
from django.http import HttpRequest
from django.utils.decorators import sync_and_async_middleware

from ninja.conf import settings as ninja_settings
from ninja.params.models import FileModel

FIX_MIDDLEWARE_PATH: str = "ninja.compatibility.files.fix_request_files_middleware"
FIX_METHODS = ninja_settings.FIX_REQUEST_FILES_METHODS


def need_to_fix_request_files(methods: List[str], params_models: List[Any]) -> bool:
    has_files_params = any(
        issubclass(model_class, FileModel) for model_class in params_models
    )
    method_needs_fix = bool(set(methods) & FIX_METHODS)
    middleware_installed = FIX_MIDDLEWARE_PATH in settings.MIDDLEWARE
    return has_files_params and method_needs_fix and not middleware_installed


@sync_and_async_middleware
def fix_request_files_middleware(get_response: Any) -> Any:
    """
    This middleware fixes long historical Django behavior where request.FILES is only
    populated for POST requests.
    https://code.djangoproject.com/ticket/12635
    """
    if iscoroutinefunction(get_response):

        async def async_middleware(request: HttpRequest) -> Any:
            if (
                request.method in FIX_METHODS
                and request.content_type != "application/json"
            ):
                initial_method = request.method
                request.method = "POST"
                request.META["REQUEST_METHOD"] = "POST"
                await sync_to_async(request._load_post_and_files)()
                request.META["REQUEST_METHOD"] = initial_method
                request.method = initial_method

            return await get_response(request)

        return async_middleware
    else:

        def sync_middleware(request: HttpRequest) -> Any:
            if (
                request.method in FIX_METHODS
                and request.content_type != "application/json"
            ):
                initial_method = request.method
                request.method = "POST"
                request.META["REQUEST_METHOD"] = "POST"
                request._load_post_and_files()
                request.META["REQUEST_METHOD"] = initial_method
                request.method = initial_method

            return get_response(request)

        return sync_middleware
