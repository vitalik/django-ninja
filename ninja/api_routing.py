from typing import (
    Any,
    List,
    Optional,
    Tuple,
    Union,
)
from ninja.throttling import BaseThrottle
from django.urls import URLPattern, URLResolver, reverse
from ninja.constants import NOT_SET, NOT_SET_TYPE
from ninja.router import Router
from ninja.openapi.urls import get_openapi_urls, get_root_url
from ninja.utils import normalize_path
from django.utils.module_loading import import_string

class RouterManager:
    def __init__(self, api: "NinjaAPI", default_router: Optional[Router] = None):
        self.api = api
        self._routers: List[Tuple[str, Router]] = []
        self.default_router = default_router or Router()
        self.add_router("", self.default_router)

    def add_router(
        self,
        prefix: str,
        router: Union[Router, str],
        *,
        auth: Any = NOT_SET,
        throttle: Union[BaseThrottle, List[BaseThrottle], NOT_SET_TYPE] = NOT_SET,
        tags: Optional[List[str]] = None,
        parent_router: Optional[Router] = None,
    ) -> None:
        if isinstance(router, str):
            router = import_string(router)
            assert isinstance(router, Router)

        if auth is not NOT_SET:
            router.auth = auth

        if throttle is not NOT_SET:
            router.throttle = throttle

        if tags is not None:
            router.tags = tags

        # Inherit API-level decorators from default router
        # Prepend API decorators so they execute first (outer decorators)
        router._decorators = self.default_router._decorators + router._decorators

        if parent_router:
            parent_prefix = next(
                (path for path, r in self._routers if r is parent_router), None
            )  # pragma: no cover
            assert parent_prefix is not None
            prefix = normalize_path("/".join((parent_prefix, prefix))).lstrip("/")

        self._routers.extend(router.build_routers(prefix))
        router.set_api_instance(self.api, parent_router)

    def _get_urls(self) -> List[Union[URLResolver, URLPattern]]:
        result = get_openapi_urls(self.api)
        
        for prefix, router in self._routers:
            result.extend(router.urls_paths(prefix))

        result.append(get_root_url(self.api))
        return result

    def get_root_path(self, path_params):
        name = f"{self.api.urls_namespace}:api-root"
        return reverse(name, kwargs=path_params)
