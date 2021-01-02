import os

from django.http import HttpRequest, HttpResponse
from ninja.openapi import get_schema
from typing import Any, List, Optional, Tuple, Sequence, Union, Callable
from django.urls import reverse
from ninja.openapi.urls import get_openapi_urls, get_root_url
from ninja.parser import Parser
from ninja.router import Router
from ninja.renderers import JSONRenderer, BaseRenderer
from ninja.errors import ConfigError
from ninja.constants import NOT_SET


class NinjaAPI:
    _registry: List[str] = []

    def __init__(
        self,
        *,
        title: str = "NinjaAPI",
        version: str = "1.0.0",
        description: str = "",
        openapi_url: Optional[str] = "/openapi.json",
        docs_url: Optional[str] = "/docs",
        urls_namespace: str = None,
        csrf: bool = False,
        auth: Union[Sequence[Callable], Callable, object] = NOT_SET,
        renderer: Optional[BaseRenderer] = None,
        parser: Optional[Parser] = None,
    ):
        self.title = title
        self.version = version
        self.description = description
        self.openapi_url = openapi_url
        self.docs_url = docs_url
        self.urls_namespace = urls_namespace or f"api-{self.version}"
        self.csrf = csrf
        self.renderer = renderer or JSONRenderer()
        self.parser = parser or Parser()

        self.auth: Optional[Sequence[Callable]] = NOT_SET
        if auth is not None and auth is not NOT_SET:
            self.auth = isinstance(auth, Sequence) and auth or [auth]

        self._routers: List[Tuple[str, Router]] = []
        self.default_router = Router()
        self.add_router("", self.default_router)

    def get(
        self,
        path: str,
        *,
        auth=NOT_SET,
        response=None,
        operation_id: Optional[str] = None,
        summary: Optional[str] = None,
        description: Optional[str] = None,
        tags: Optional[List[str]] = None,
        deprecated: Optional[bool] = None,
    ):
        return self.default_router.get(
            path,
            auth=auth is NOT_SET and self.auth or auth,
            response=response,
            operation_id=operation_id,
            summary=summary,
            description=description,
            tags=tags,
            deprecated=deprecated,
        )

    def post(
        self,
        path: str,
        *,
        auth=NOT_SET,
        response=None,
        operation_id: Optional[str] = None,
        summary: Optional[str] = None,
        description: Optional[str] = None,
        tags: Optional[List[str]] = None,
        deprecated: Optional[bool] = None,
    ):
        return self.default_router.post(
            path,
            auth=auth is NOT_SET and self.auth or auth,
            response=response,
            operation_id=operation_id,
            summary=summary,
            description=description,
            tags=tags,
            deprecated=deprecated,
        )

    def delete(
        self,
        path: str,
        *,
        auth=NOT_SET,
        response=None,
        operation_id: Optional[str] = None,
        summary: Optional[str] = None,
        description: Optional[str] = None,
        tags: Optional[List[str]] = None,
        deprecated: Optional[bool] = None,
    ):
        return self.default_router.delete(
            path,
            auth=auth is NOT_SET and self.auth or auth,
            response=response,
            operation_id=operation_id,
            summary=summary,
            description=description,
            tags=tags,
            deprecated=deprecated,
        )

    def patch(
        self,
        path: str,
        *,
        auth=NOT_SET,
        response=None,
        operation_id: Optional[str] = None,
        summary: Optional[str] = None,
        description: Optional[str] = None,
        tags: Optional[List[str]] = None,
        deprecated: Optional[bool] = None,
    ):
        return self.default_router.patch(
            path,
            auth=auth is NOT_SET and self.auth or auth,
            response=response,
            operation_id=operation_id,
            summary=summary,
            description=description,
            tags=tags,
            deprecated=deprecated,
        )

    def put(
        self,
        path: str,
        *,
        auth=NOT_SET,
        response=None,
        operation_id: Optional[str] = None,
        summary: Optional[str] = None,
        description: Optional[str] = None,
        tags: Optional[List[str]] = None,
        deprecated: Optional[bool] = None,
    ):
        return self.default_router.put(
            path,
            auth=auth is NOT_SET and self.auth or auth,
            response=response,
            operation_id=operation_id,
            summary=summary,
            description=description,
            tags=tags,
            deprecated=deprecated,
        )

    def api_operation(
        self,
        methods: List[str],
        path: str,
        *,
        auth=NOT_SET,
        response=None,
        operation_id: Optional[str] = None,
        summary: Optional[str] = None,
        description: Optional[str] = None,
        tags: Optional[List[str]] = None,
        deprecated: Optional[bool] = None,
    ):
        return self.default_router.api_operation(
            methods,
            path,
            auth=auth is NOT_SET and self.auth or auth,
            response=response,
            operation_id=operation_id,
            summary=summary,
            description=description,
            tags=tags,
            deprecated=deprecated,
        )

    def add_router(self, prefix, router):
        self._routers.extend(router.build_routers(prefix))
        router.set_api_instance(self)

    @property
    def urls(self):
        self._validate()
        return (
            self._get_urls(),
            "ninja",
            self.urls_namespace.split(":")[-1],
            # ^ if api included into nested urls, we only care about last bit here
        )

    def _get_urls(self):
        result = get_openapi_urls(self)

        for prefix, router in self._routers:
            for path in router.urls_paths(prefix):
                result.append(path)

        result.append(get_root_url(self))
        return result

    @property
    def root_path(self):
        name = f"{self.urls_namespace}:api-root"
        return reverse(name)

    def create_response(self, request: HttpRequest, data: Any, status: int = 200):
        content = self.renderer.render(request, data, response_status=status)
        content_type = "{}; charset={}".format(
            self.renderer.media_type, self.renderer.charset
        )
        return HttpResponse(content, status=status, content_type=content_type)

    def get_openapi_schema(self, path_prefix=None):
        if path_prefix is None:
            path_prefix = self.root_path
        return get_schema(api=self, path_prefix=path_prefix)

    def get_openapi_operation_id(self, operation: "Operation"):
        name = operation.view_func.__name__
        module = operation.view_func.__module__
        return (module + "_" + name).replace(".", "_")

    def _validate(self):
        from ninja.security import APIKeyCookie

        # 1) urls namespacing validation
        skip_registry = os.environ.get("NINJA_SKIP_REGISTRY", False)
        if not skip_registry and self.urls_namespace in NinjaAPI._registry:
            msg = [
                "Looks like you created multiple NinjaAPIs",
                "To let ninja distinguish them you need to set either unique version or url_namespace",
                " - NinjaAPI(..., version='2.0.0')",
                " - NinjaAPI(..., urls_namespace='otherapi')",
                f"Already registered: {NinjaAPI._registry}",
            ]
            raise ConfigError("\n".join(msg))
        NinjaAPI._registry.append(self.urls_namespace)

        # 2) csrf
        if self.csrf is False:
            for _prefix, router in self._routers:
                for path_operation in router.operations.values():
                    for operation in path_operation.operations:
                        for auth in operation.auth_callbacks:
                            if isinstance(auth, APIKeyCookie):
                                raise ConfigError(
                                    "Cookie Authentication must be used with CSRF. Please use NinjaAPI(csrf=True)"
                                )
