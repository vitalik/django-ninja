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
from django.urls import URLPattern, URLResolver, reverse

from ninja.constants import NOT_SET, NOT_SET_TYPE
from ninja.errors import ConfigError, set_default_exc_handlers
from ninja.openapi import get_schema
from ninja.openapi.schema import OpenAPISchema
from ninja.openapi.urls import get_openapi_urls, get_root_url
from ninja.parser import Parser
from ninja.renderers import BaseRenderer, JSONRenderer
from ninja.router import Router
from ninja.types import TCallable
from ninja.utils import is_debug_server, normalize_path

if TYPE_CHECKING:
    from .operation import Operation  # pragma: no cover

__all__ = ["NinjaAPI"]

Exc = Union[Exception, Type[Exception]]
ExcHandler = Callable[[HttpRequest, Exc], HttpResponse]


class NinjaAPI:
    """
    Ninja API
    """

    _registry: List[str] = []

    def __init__(
        self,
        *,
        title: str = "NinjaAPI",
        version: str = "1.0.0",
        description: str = "",
        openapi_url: Optional[str] = "/openapi.json",
        docs_url: Optional[str] = "/docs",
        servers: Optional[List[Dict[str, Union[str, Any]]]] = None,
        docs_decorator: Optional[Callable[[TCallable], TCallable]] = None,
        urls_namespace: Optional[str] = None,
        csrf: bool = False,
        auth: Optional[Union[Sequence[Callable], Callable, NOT_SET_TYPE]] = NOT_SET,
        renderer: Optional[BaseRenderer] = None,
        parser: Optional[Parser] = None,
        default_router: Optional[Router] = None,
        openapi_extra: Optional[Dict[str, Any]] = None,
    ):
        """
        Args:
            title: A title for the api.
            description: A description for the api.
            version: The API version.
            urls_namespace: The Django URL namespace for the API. If not provided, the namespace will be ``"api-" + self.version``.
            openapi_url: The relative URL to serve the openAPI spec.
            openapi_extra: Additional attributes for the openAPI spec.
            docs_url: The relative URL to serve the API docs.
            servers: List of target hosts used in openAPI spec.
            csrf: Require a CSRF token for unsafe request types. See <a href="../csrf">CSRF</a> docs.
            auth (Callable | Sequence[Callable] | NOT_SET | None): Authentication class
            renderer: Default response renderer
            parser: Default request parser
        """
        self.title = title
        self.version = version
        self.description = description
        self.openapi_url = openapi_url
        self.docs_url = docs_url
        self.servers = servers
        self.docs_decorator = docs_decorator
        self.urls_namespace = urls_namespace or f"api-{self.version}"
        self.csrf = csrf
        self.renderer = renderer or JSONRenderer()
        self.parser = parser or Parser()
        self.openapi_extra = openapi_extra or {}

        self._exception_handlers: Dict[Exc, ExcHandler] = {}
        self.set_default_exception_handlers()

        self.auth: Optional[Union[Sequence[Callable], NOT_SET_TYPE]]

        if callable(auth):
            self.auth = [auth]
        else:
            self.auth = auth

        self._routers: List[Tuple[str, Router]] = []
        self.default_router = default_router or Router()
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
        openapi_extra: Optional[Dict[str, Any]] = None,
    ) -> Callable[[TCallable], TCallable]:
        """
        `GET` operation. See <a href="../operations-parameters">operations
        parameters</a> reference.
        """
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
            openapi_extra=openapi_extra,
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
        openapi_extra: Optional[Dict[str, Any]] = None,
    ) -> Callable[[TCallable], TCallable]:
        """
        `POST` operation. See <a href="../operations-parameters">operations
        parameters</a> reference.
        """
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
            openapi_extra=openapi_extra,
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
        openapi_extra: Optional[Dict[str, Any]] = None,
    ) -> Callable[[TCallable], TCallable]:
        """
        `DELETE` operation. See <a href="../operations-parameters">operations
        parameters</a> reference.
        """
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
            openapi_extra=openapi_extra,
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
        openapi_extra: Optional[Dict[str, Any]] = None,
    ) -> Callable[[TCallable], TCallable]:
        """
        `PATCH` operation. See <a href="../operations-parameters">operations
        parameters</a> reference.
        """
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
            openapi_extra=openapi_extra,
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
        openapi_extra: Optional[Dict[str, Any]] = None,
    ) -> Callable[[TCallable], TCallable]:
        """
        `PUT` operation. See <a href="../operations-parameters">operations
        parameters</a> reference.
        """
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
            openapi_extra=openapi_extra,
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
        openapi_extra: Optional[Dict[str, Any]] = None,
    ) -> Callable[[TCallable], TCallable]:
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
            openapi_extra=openapi_extra,
        )

    def add_router(
        self,
        prefix: str,
        router: Router,
        *,
        auth: Any = NOT_SET,
        tags: Optional[List[str]] = None,
        parent_router: Router = None,
    ) -> None:
        if auth is not NOT_SET:
            router.auth = auth
        if tags is not None:
            router.tags = tags

        if parent_router:
            parent_prefix = next(
                (path for path, r in self._routers if r is parent_router), None
            )  # pragma: no cover
            assert parent_prefix is not None
            prefix = normalize_path("/".join((parent_prefix, prefix))).lstrip("/")

        self._routers.extend(router.build_routers(prefix))
        router.set_api_instance(self, parent_router)

    @property
    def urls(self) -> Tuple[List[Union[URLResolver, URLPattern]], str, str]:
        """
        str: URL configuration

        Returns:

            Django URL configuration
        """
        self._validate()
        return (
            self._get_urls(),
            "ninja",
            self.urls_namespace.split(":")[-1],
            # ^ if api included into nested urls, we only care about last bit here
        )

    def _get_urls(self) -> List[Union[URLResolver, URLPattern]]:
        result = get_openapi_urls(self)

        for prefix, router in self._routers:
            result.extend(router.urls_paths(prefix))

        result.append(get_root_url(self))
        return result

    @property
    def root_path(self) -> str:
        name = f"{self.urls_namespace}:api-root"
        return reverse(name)

    def create_response(
        self,
        request: HttpRequest,
        data: Any,
        *,
        status: int = None,
        temporal_response: HttpResponse = None,
    ) -> HttpResponse:
        if temporal_response:
            status = temporal_response.status_code
        assert status

        content = self.renderer.render(request, data, response_status=status)

        if temporal_response:
            response = temporal_response
            response.content = content
        else:
            response = HttpResponse(
                content, status=status, content_type=self.get_content_type()
            )

        return response

    def create_temporal_response(self, request: HttpRequest) -> HttpResponse:
        return HttpResponse("", content_type=self.get_content_type())

    def get_content_type(self) -> str:
        return "{}; charset={}".format(self.renderer.media_type, self.renderer.charset)

    def get_openapi_schema(self, path_prefix: Optional[str] = None) -> OpenAPISchema:
        if path_prefix is None:
            path_prefix = self.root_path
        return get_schema(api=self, path_prefix=path_prefix)

    def get_openapi_operation_id(self, operation: "Operation") -> str:
        name = operation.view_func.__name__
        module = operation.view_func.__module__
        return (module + "_" + name).replace(".", "_")

    def get_operation_url_name(self, operation: "Operation", router: Router) -> str:
        """
        Get the default URL name to use for an operation if it wasn't
        explicitly provided.
        """
        return operation.view_func.__name__

    def add_exception_handler(
        self, exc_class: Type[Exception], handler: ExcHandler
    ) -> None:
        assert issubclass(exc_class, Exception)
        self._exception_handlers[exc_class] = handler

    def exception_handler(self, exc_class: Type[Exception]) -> Callable[..., Any]:
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
        if (
            not skip_registry
            and self.urls_namespace in NinjaAPI._registry
            and not debug_server_url_reimport()
        ):
            msg = f"""
Looks like you created multiple NinjaAPIs or TestClients
To let ninja distinguish them you need to set either unique version or urls_namespace
 - NinjaAPI(..., version='2.0.0')
 - NinjaAPI(..., urls_namespace='otherapi')
Already registered: {NinjaAPI._registry}
"""
            raise ConfigError(msg.strip())
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


_imported_while_running_in_debug_server = is_debug_server()


def debug_server_url_reimport() -> bool:
    """
    Detect reimport of URL module to allow error to propagate to developer.

    When Django loads urls it uses: ``django.urls.resolvers.urlconf_module()``

    ```Python
    @cached_property
    def urlconf_module(self):
        if isinstance(self.urlconf_name, str):
            return import_module(self.urlconf_name)
        else:
            return self.urlconf_name
    ```

    This uses ``@cached_property`` to generally only import once.  But if the
    import throws an error when using the development server, the following
    code in ``django.utils.autoreload.BaseReloader.run()`` is used:

    ```Python
    # Prevent a race condition where URL modules aren't loaded when the
    # reloader starts by accessing the urlconf_module property.
    try:
        get_resolver().urlconf_module
    except Exception:
        # Loading the urlconf can result in errors during development.
        # If this occurs then swallow the error and continue.
        pass
    ```

    This means the (likely) developer error that caused the Exception is
    initially ignored. This is not generally a problem since the error will
    usually be exercised again, and reported at that time.  But Ninja has
    various code which guards against errors where items that cannot be reused,
    are attempted to be reused.  This results in Ninja throwing a false error,
    and hiding the true error from the developer when running under the
    development server.

    Returns:

        True if this module was originally imported during Django dev-server
        init but the caller is not being running during Django dev-server init.
    """
    return _imported_while_running_in_debug_server and not is_debug_server()
