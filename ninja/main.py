import os
from typing import (
    TYPE_CHECKING,
    Any,
    Callable,
    Dict,
    List,
    Optional,
    Sequence,
    Tuple,
    Type,
    Union,
)

from django.http import HttpRequest, HttpResponse
from django.urls import URLPattern, reverse

from ninja.constants import NOT_SET
from ninja.errors import ConfigError, set_default_exc_handlers
from ninja.openapi import get_schema
from ninja.openapi.schema import OpenAPISchema
from ninja.openapi.urls import get_openapi_urls, get_root_url
from ninja.parser import Parser
from ninja.renderers import BaseRenderer, JSONRenderer
from ninja.router import Decorator, Router

if TYPE_CHECKING:
    from .operation import Operation  # pragma: no cover

__all__ = ["NinjaAPI"]

Exc = Union[Exception, Type[Exception]]
ExcHandler = Callable[[HttpRequest, Exc], HttpResponse]


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
        urls_namespace: Optional[str] = None,
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

        self._exception_handlers: Dict[Exc, ExcHandler] = {}
        self.set_default_exception_handlers()

        self.auth: Optional[Sequence[Callable]] = NOT_SET
        if auth is not None and auth is not NOT_SET:
            self.auth = isinstance(auth, Sequence) and auth or [auth]  # type: ignore

        self._routers: List[Tuple[str, Router]] = []
        self.default_router = Router()
        self.add_router("", self.default_router)

    def get(
        self,
        path: str,
        *,
        auth: Any = NOT_SET,
        response: Any = NOT_SET,
        operation_id: Optional[str] = None,
        summary: Optional[str] = None,
        description: Optional[str] = None,
        tags: Optional[List[str]] = None,
        deprecated: Optional[bool] = None,
        by_alias: bool = False,
        exclude_unset: bool = False,
        exclude_defaults: bool = False,
        exclude_none: bool = False,
        url_name: Optional[str] = None,
        include_in_schema: bool = True,
    ) -> Decorator:
        return self.default_router.get(
            path,
            auth=auth is NOT_SET and self.auth or auth,
            response=response,
            operation_id=operation_id,
            summary=summary,
            description=description,
            tags=tags,
            deprecated=deprecated,
            by_alias=by_alias,
            exclude_unset=exclude_unset,
            exclude_defaults=exclude_defaults,
            exclude_none=exclude_none,
            url_name=url_name,
            include_in_schema=include_in_schema,
        )

    def post(
        self,
        path: str,
        *,
        auth: Any = NOT_SET,
        response: Any = NOT_SET,
        operation_id: Optional[str] = None,
        summary: Optional[str] = None,
        description: Optional[str] = None,
        tags: Optional[List[str]] = None,
        deprecated: Optional[bool] = None,
        by_alias: bool = False,
        exclude_unset: bool = False,
        exclude_defaults: bool = False,
        exclude_none: bool = False,
        url_name: Optional[str] = None,
        include_in_schema: bool = True,
    ) -> Decorator:
        return self.default_router.post(
            path,
            auth=auth is NOT_SET and self.auth or auth,
            response=response,
            operation_id=operation_id,
            summary=summary,
            description=description,
            tags=tags,
            deprecated=deprecated,
            by_alias=by_alias,
            exclude_unset=exclude_unset,
            exclude_defaults=exclude_defaults,
            exclude_none=exclude_none,
            url_name=url_name,
            include_in_schema=include_in_schema,
        )

    def delete(
        self,
        path: str,
        *,
        auth: Any = NOT_SET,
        response: Any = NOT_SET,
        operation_id: Optional[str] = None,
        summary: Optional[str] = None,
        description: Optional[str] = None,
        tags: Optional[List[str]] = None,
        deprecated: Optional[bool] = None,
        by_alias: bool = False,
        exclude_unset: bool = False,
        exclude_defaults: bool = False,
        exclude_none: bool = False,
        url_name: Optional[str] = None,
        include_in_schema: bool = True,
    ) -> Decorator:
        return self.default_router.delete(
            path,
            auth=auth is NOT_SET and self.auth or auth,
            response=response,
            operation_id=operation_id,
            summary=summary,
            description=description,
            tags=tags,
            deprecated=deprecated,
            by_alias=by_alias,
            exclude_unset=exclude_unset,
            exclude_defaults=exclude_defaults,
            exclude_none=exclude_none,
            url_name=url_name,
            include_in_schema=include_in_schema,
        )

    def patch(
        self,
        path: str,
        *,
        auth: Any = NOT_SET,
        response: Any = NOT_SET,
        operation_id: Optional[str] = None,
        summary: Optional[str] = None,
        description: Optional[str] = None,
        tags: Optional[List[str]] = None,
        deprecated: Optional[bool] = None,
        by_alias: bool = False,
        exclude_unset: bool = False,
        exclude_defaults: bool = False,
        exclude_none: bool = False,
        url_name: Optional[str] = None,
        include_in_schema: bool = True,
    ) -> Decorator:
        return self.default_router.patch(
            path,
            auth=auth is NOT_SET and self.auth or auth,
            response=response,
            operation_id=operation_id,
            summary=summary,
            description=description,
            tags=tags,
            deprecated=deprecated,
            by_alias=by_alias,
            exclude_unset=exclude_unset,
            exclude_defaults=exclude_defaults,
            exclude_none=exclude_none,
            url_name=url_name,
            include_in_schema=include_in_schema,
        )

    def put(
        self,
        path: str,
        *,
        auth: Any = NOT_SET,
        response: Any = NOT_SET,
        operation_id: Optional[str] = None,
        summary: Optional[str] = None,
        description: Optional[str] = None,
        tags: Optional[List[str]] = None,
        deprecated: Optional[bool] = None,
        by_alias: bool = False,
        exclude_unset: bool = False,
        exclude_defaults: bool = False,
        exclude_none: bool = False,
        url_name: Optional[str] = None,
        include_in_schema: bool = True,
    ) -> Decorator:
        return self.default_router.put(
            path,
            auth=auth is NOT_SET and self.auth or auth,
            response=response,
            operation_id=operation_id,
            summary=summary,
            description=description,
            tags=tags,
            deprecated=deprecated,
            by_alias=by_alias,
            exclude_unset=exclude_unset,
            exclude_defaults=exclude_defaults,
            exclude_none=exclude_none,
            url_name=url_name,
            include_in_schema=include_in_schema,
        )

    def api_operation(
        self,
        methods: List[str],
        path: str,
        *,
        auth: Any = NOT_SET,
        response: Any = NOT_SET,
        operation_id: Optional[str] = None,
        summary: Optional[str] = None,
        description: Optional[str] = None,
        tags: Optional[List[str]] = None,
        deprecated: Optional[bool] = None,
        by_alias: bool = False,
        exclude_unset: bool = False,
        exclude_defaults: bool = False,
        exclude_none: bool = False,
        url_name: Optional[str] = None,
        include_in_schema: bool = True,
    ) -> Decorator:
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
            by_alias=by_alias,
            exclude_unset=exclude_unset,
            exclude_defaults=exclude_defaults,
            exclude_none=exclude_none,
            url_name=url_name,
            include_in_schema=include_in_schema,
        )

    def add_router(
        self,
        prefix: str,
        router: Router,
        *,
        auth: Any = NOT_SET,
        tags: Optional[List[str]] = None,
    ) -> None:
        if auth != NOT_SET:
            router.auth = auth
        if tags is not None:
            router.tags = tags
        self._routers.extend(router.build_routers(prefix))
        router.set_api_instance(self)

    @property
    def urls(self) -> Tuple[Any, ...]:
        self._validate()
        return (
            self._get_urls(),
            "ninja",
            self.urls_namespace.split(":")[-1],
            # ^ if api included into nested urls, we only care about last bit here
        )

    def _get_urls(self) -> List[URLPattern]:
        result = get_openapi_urls(self)

        for prefix, router in self._routers:
            for path in router.urls_paths(prefix):
                result.append(path)

        result.append(get_root_url(self))
        return result

    @property
    def root_path(self) -> str:
        name = f"{self.urls_namespace}:api-root"
        return reverse(name)

    def create_response(
        self, request: HttpRequest, data: Any, *, status: int = 200
    ) -> HttpResponse:
        content = self.renderer.render(request, data, response_status=status)
        content_type = "{}; charset={}".format(
            self.renderer.media_type, self.renderer.charset
        )
        return HttpResponse(content, status=status, content_type=content_type)

    def get_openapi_schema(self, path_prefix: Optional[str] = None) -> OpenAPISchema:
        if path_prefix is None:
            path_prefix = self.root_path
        return get_schema(api=self, path_prefix=path_prefix)

    def get_openapi_operation_id(self, operation: "Operation") -> str:
        name = operation.view_func.__name__
        module = operation.view_func.__module__
        return (module + "_" + name).replace(".", "_")

    def add_exception_handler(
        self, exc_class: Type[Exception], handler: ExcHandler
    ) -> None:
        assert issubclass(exc_class, Exception)
        self._exception_handlers[exc_class] = handler

    def exception_handler(self, exc_class: Type[Exception]) -> Callable:
        def decorator(func: Callable) -> Callable:
            self.add_exception_handler(exc_class, func)
            return func

        return decorator

    def set_default_exception_handlers(self) -> None:
        set_default_exc_handlers(self)

    def on_exception(self, request: HttpRequest, exc: Exc) -> HttpResponse:
        handler = self._lookup_exception_handler(exc)
        if handler is None:
            raise exc
        return handler(request, exc)

    def _lookup_exception_handler(self, exc: Exc) -> Optional[ExcHandler]:
        for cls in type(exc).__mro__:
            if cls in self._exception_handlers:
                return self._exception_handlers[cls]

        return None

    def _validate(self) -> None:
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
                for path_operation in router.path_operations.values():
                    for operation in path_operation.operations:
                        for auth in operation.auth_callbacks:
                            if isinstance(auth, APIKeyCookie):
                                raise ConfigError(
                                    "Cookie Authentication must be used with CSRF. Please use NinjaAPI(csrf=True)"
                                )
