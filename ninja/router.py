import re
import warnings
from dataclasses import dataclass, field
from typing import (
    TYPE_CHECKING,
    Any,
    Callable,
    Dict,
    Iterator,
    List,
    Optional,
    Tuple,
    Union,
    overload,
)

from django.urls import URLPattern
from django.urls import path as django_path
from django.utils.module_loading import import_string

from ninja.constants import NOT_SET, NOT_SET_TYPE
from ninja.decorators import DecoratorMode
from ninja.errors import ConfigError
from ninja.operation import PathView
from ninja.throttling import BaseThrottle
from ninja.types import TCallable, TSchemaClass
from ninja.utils import normalize_path, replace_path_param_notation
from ninja.webhooks import Webhook
from ninja.websockets.operation import WebSocketOperation

if TYPE_CHECKING:
    from ninja import NinjaAPI  # pragma: no cover


__all__ = ["Router", "RouterMount", "BoundRouter"]


def _keep_uuid_as_string(path: str) -> str:
    """
    Django's ``uuid`` converter turns the value into a UUID object; ninja uses
    its own ``uuidstr`` converter to keep strings and let pydantic handle the
    conversion/validation (if the user annotates the param as UUID).
    """
    return re.sub(r"\{uuid:(\w+)\}", r"{uuidstr:\1}", path, flags=re.IGNORECASE)


@dataclass
class RouterMount:
    """
    Configuration for how a Router template is mounted to an API.

    This class stores the mount-time configuration without mutating the
    original Router template, enabling router reuse across multiple APIs
    or multiple mount points within the same API.
    """

    template: "Router"
    prefix: str
    url_name_prefix: Optional[str] = None
    auth: Any = NOT_SET
    throttle: Any = NOT_SET
    tags: Optional[List[str]] = None
    inherited_decorators: List[Tuple[Callable, DecoratorMode]] = field(
        default_factory=list
    )
    # Inherited auth/throttle/tags from parent routers (for nested router inheritance)
    inherited_auth: Any = NOT_SET
    inherited_throttle: Any = NOT_SET
    inherited_tags: Optional[List[str]] = None


class BoundRouter:
    """
    A Router template bound to a specific API instance.

    Contains cloned operations with decorators applied. Each mount of a router
    creates a new BoundRouter instance, ensuring complete isolation between mounts.
    """

    def __init__(self, mount: RouterMount, api: "NinjaAPI") -> None:
        self.mount = mount
        self.template = mount.template
        self.api = api
        self.prefix = mount.prefix
        self.url_name_prefix = mount.url_name_prefix

        # Effective settings priority:
        # 1. mount override (from api.add_router auth/throttle/tags params on this specific mount)
        # 2. template's own settings (set on the Router itself)
        # 3. inherited from parent (for nested routers where parent has auth)
        if mount.auth is not NOT_SET:
            self.auth = mount.auth
        elif mount.template.auth is not NOT_SET:
            self.auth = mount.template.auth
        elif mount.inherited_auth is not NOT_SET:
            self.auth = mount.inherited_auth
        else:
            self.auth = NOT_SET

        if mount.throttle is not NOT_SET:
            self.throttle = mount.throttle
        elif mount.template.throttle is not NOT_SET:
            self.throttle = mount.template.throttle
        elif mount.inherited_throttle is not NOT_SET:
            self.throttle = mount.inherited_throttle
        else:
            self.throttle = NOT_SET

        # Tags handling (issue #794):
        # - mount.tags (from add_router call) = explicit override, use as-is
        # - Otherwise, accumulate: inherited tags + template's own tags
        self.tags: Optional[List[str]]
        if mount.tags is not None:
            # Explicit tags from add_router() call - use as override
            self.tags = mount.tags
        else:
            # Accumulate inherited tags with template's own tags
            accumulated_tags: List[str] = []
            if mount.inherited_tags is not None:
                accumulated_tags.extend(mount.inherited_tags)
            if mount.template.tags is not None:
                accumulated_tags.extend(mount.template.tags)
            self.tags = accumulated_tags or None

        # Clone operations and apply decorators
        self.path_operations: Dict[str, PathView] = {}
        self._bind_operations()
        self.websocket_operations: Dict[str, WebSocketOperation] = {}
        self._bind_websocket_operations()

    def _inherited_throttle_objects(self) -> Optional[List[BaseThrottle]]:
        """Throttles from this mount/router, falling back to the API ones."""
        throttle = self.throttle if self.throttle != NOT_SET else self.api.throttle
        if throttle == NOT_SET:
            return None
        if throttle is None:  # explicit "no throttling" (as on master)
            return []
        if isinstance(throttle, BaseThrottle):
            return [throttle]
        return list(throttle)

    def _bind_websocket_operations(self) -> None:
        websocket_operations = self.template.websocket_operations
        decorators = self.mount.inherited_decorators + self.template._decorators
        if websocket_operations and decorators:
            names = ", ".join(
                op.view_func.__name__ for op in websocket_operations.values()
            )
            warnings.warn(
                "Decorators added with add_decorator() are not applied to "
                f"websocket handlers ({names}): they wrap HTTP views/operations.",
                UserWarning,
                stacklevel=2,
            )

        for path, ws_operation in websocket_operations.items():
            operation = ws_operation.clone()
            operation.api = self.api
            if operation.auth_param == NOT_SET:
                if self.auth != NOT_SET:
                    operation._set_auth(self.auth)
                elif self.api.auth != NOT_SET:
                    operation._set_auth(self.api.auth)
            if operation.throttle_param == NOT_SET:
                inherited = self._inherited_throttle_objects()
                if inherited is not None:
                    operation.throttle_objects = inherited
            self.websocket_operations[path] = operation

    def websocket_routes(self, prefix: str) -> Iterator[Tuple[str, WebSocketOperation]]:
        """Yield (django route, operation) for every websocket endpoint."""
        prefix = replace_path_param_notation(prefix)
        for path, operation in self.websocket_operations.items():
            path = replace_path_param_notation(path)
            route = "/".join([i for i in (prefix, path) if i])
            yield normalize_path(route).lstrip("/"), operation

    def _bind_operations(self) -> None:
        """Clone operations from template and apply effective settings."""
        effective_decorators = (
            self.mount.inherited_decorators + self.template._decorators
        )

        for path, path_view in self.template.path_operations.items():
            cloned_view = path_view.clone()

            for operation in cloned_view.operations:
                # Bind to API
                operation.api = self.api

                # Apply auth inheritance
                if operation.auth_param == NOT_SET:
                    if self.auth != NOT_SET:
                        operation._set_auth(self.auth)
                    elif self.api.auth != NOT_SET:
                        operation._set_auth(self.api.auth)

                # Apply throttle inheritance
                if operation.throttle_param == NOT_SET:
                    inherited = self._inherited_throttle_objects()
                    if inherited is not None:
                        operation.throttle_objects = inherited

                # Apply tags inheritance
                if operation.tags is None and self.tags is not None:  # type: ignore[has-type]
                    operation.tags = self.tags  # type: ignore[has-type]

                # Apply decorators (fresh application - no tracking needed)
                for decorator, mode in effective_decorators:
                    if mode == "view":
                        operation.run = decorator(operation.run)  # type: ignore
                    elif mode == "operation":
                        operation.view_func = decorator(operation.view_func)
                    else:
                        raise ValueError(
                            f"Invalid decorator mode: {mode}"
                        )  # pragma: no cover

            self.path_operations[path] = cloned_view

    def urls_paths(self, prefix: str) -> Iterator[URLPattern]:
        """
        Generate URL patterns for this bound router, in declaration order
        (HTTP and websocket routes alike), since Django uses the first match.
        """
        prefix = replace_path_param_notation(prefix)
        for path in self._ordered_paths():
            route = "/".join([
                i for i in (prefix, replace_path_param_notation(path)) if i
            ])
            route = normalize_path(route).lstrip("/")
            path_view = self.path_operations.get(path)
            ws_operation = self.websocket_operations.get(path)
            if path_view is not None:
                yield from self._http_patterns(route, path_view, ws_operation)
            if ws_operation is not None:
                # An HTTP view answering how to connect: it makes the websocket
                # resolvable and reversible. For a path shared with HTTP
                # operations it comes after them, so HTTP requests reach those.
                yield django_path(
                    route,
                    ws_operation.get_http_view(),
                    name=self._websocket_url_name(ws_operation),
                )

    def _ordered_paths(self) -> List[str]:
        paths = list(self.template._route_order)
        known = set(paths)
        # paths added without the Router API (e.g. directly to path_operations)
        for path in [*self.path_operations, *self.websocket_operations]:
            if path not in known:
                known.add(path)
                paths.append(path)
        return paths

    def _http_patterns(
        self,
        route: str,
        path_view: PathView,
        ws_operation: Optional[WebSocketOperation],
    ) -> Iterator[URLPattern]:
        for operation in path_view.operations:
            url_name = getattr(operation, "url_name", "")
            if not url_name:
                url_name = self.api.get_operation_url_name(
                    operation, router=self.template
                )
                # Apply url_name_prefix if specified
                if self.url_name_prefix and url_name:
                    url_name = f"{self.url_name_prefix}_{url_name}"

            view = path_view.get_view()
            if ws_operation is not None:
                # same path serves HTTP and websocket: the ASGI dispatcher
                # finds the websocket operation through this attribute
                view.ninja_websocket_operation = ws_operation  # type: ignore
            yield django_path(route, view, name=url_name)

    def _websocket_url_name(self, ws_operation: WebSocketOperation) -> str:
        if ws_operation.url_name:
            return ws_operation.url_name
        url_name = ws_operation.view_func.__name__
        if self.url_name_prefix:
            url_name = f"{self.url_name_prefix}_{url_name}"
        return url_name


class Router:
    def __init__(
        self,
        *,
        auth: Any = NOT_SET,
        throttle: Union[BaseThrottle, List[BaseThrottle], NOT_SET_TYPE] = NOT_SET,
        tags: Optional[List[str]] = None,
        by_alias: Optional[bool] = None,
        exclude_unset: Optional[bool] = None,
        exclude_defaults: Optional[bool] = None,
        exclude_none: Optional[bool] = None,
    ) -> None:
        self._frozen = False
        self.auth = auth
        self.throttle = throttle
        self.tags = tags
        self.by_alias = by_alias
        self.exclude_unset = exclude_unset
        self.exclude_defaults = exclude_defaults
        self.exclude_none = exclude_none

        self.path_operations: Dict[str, PathView] = {}
        self.websocket_operations: Dict[str, WebSocketOperation] = {}
        # first registration order of every path (HTTP and websocket), used
        # to generate URL patterns in declaration order
        self._route_order: List[str] = []
        self.webhooks: Dict[str, Webhook] = {}
        self._routers: List[Tuple[str, Router, Optional[List[str]]]] = []
        # (auth, throttle) passed to add_router(), aligned with self._routers
        self._router_overrides: List[Tuple[Any, Any]] = []
        self._decorators: List[Tuple[Callable, DecoratorMode]] = []

    def _freeze(self) -> None:
        """Mark router as frozen - no more modifications allowed."""
        self._frozen = True
        for _, child_router, _ in self._routers:
            child_router._freeze()

    def _check_not_frozen(self) -> None:
        """Raise error if attempting to modify a frozen router."""
        if self._frozen:
            raise ConfigError(
                "Cannot modify router after URLs have been generated. "
                "Routers become frozen when api.urls is accessed."
            )

    def get(
        self,
        path: str,
        *,
        auth: Any = NOT_SET,
        throttle: Union[BaseThrottle, List[BaseThrottle], NOT_SET_TYPE] = NOT_SET,
        response: Any = NOT_SET,
        operation_id: Optional[str] = None,
        summary: Optional[str] = None,
        description: Optional[str] = None,
        tags: Optional[List[str]] = None,
        deprecated: Optional[bool] = None,
        by_alias: Optional[bool] = None,
        exclude_unset: Optional[bool] = None,
        exclude_defaults: Optional[bool] = None,
        exclude_none: Optional[bool] = None,
        url_name: Optional[str] = None,
        include_in_schema: bool = True,
        openapi_extra: Optional[Dict[str, Any]] = None,
    ) -> Callable[[TCallable], TCallable]:
        return self.api_operation(
            ["GET"],
            path,
            auth=auth,
            throttle=throttle,
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
        throttle: Union[BaseThrottle, List[BaseThrottle], NOT_SET_TYPE] = NOT_SET,
        response: Any = NOT_SET,
        operation_id: Optional[str] = None,
        summary: Optional[str] = None,
        description: Optional[str] = None,
        tags: Optional[List[str]] = None,
        deprecated: Optional[bool] = None,
        by_alias: Optional[bool] = None,
        exclude_unset: Optional[bool] = None,
        exclude_defaults: Optional[bool] = None,
        exclude_none: Optional[bool] = None,
        url_name: Optional[str] = None,
        include_in_schema: bool = True,
        openapi_extra: Optional[Dict[str, Any]] = None,
    ) -> Callable[[TCallable], TCallable]:
        return self.api_operation(
            ["POST"],
            path,
            auth=auth,
            throttle=throttle,
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
        throttle: Union[BaseThrottle, List[BaseThrottle], NOT_SET_TYPE] = NOT_SET,
        response: Any = NOT_SET,
        operation_id: Optional[str] = None,
        summary: Optional[str] = None,
        description: Optional[str] = None,
        tags: Optional[List[str]] = None,
        deprecated: Optional[bool] = None,
        by_alias: Optional[bool] = None,
        exclude_unset: Optional[bool] = None,
        exclude_defaults: Optional[bool] = None,
        exclude_none: Optional[bool] = None,
        url_name: Optional[str] = None,
        include_in_schema: bool = True,
        openapi_extra: Optional[Dict[str, Any]] = None,
    ) -> Callable[[TCallable], TCallable]:
        return self.api_operation(
            ["DELETE"],
            path,
            auth=auth,
            throttle=throttle,
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
        throttle: Union[BaseThrottle, List[BaseThrottle], NOT_SET_TYPE] = NOT_SET,
        response: Any = NOT_SET,
        operation_id: Optional[str] = None,
        summary: Optional[str] = None,
        description: Optional[str] = None,
        tags: Optional[List[str]] = None,
        deprecated: Optional[bool] = None,
        by_alias: Optional[bool] = None,
        exclude_unset: Optional[bool] = None,
        exclude_defaults: Optional[bool] = None,
        exclude_none: Optional[bool] = None,
        url_name: Optional[str] = None,
        include_in_schema: bool = True,
        openapi_extra: Optional[Dict[str, Any]] = None,
    ) -> Callable[[TCallable], TCallable]:
        return self.api_operation(
            ["PATCH"],
            path,
            auth=auth,
            throttle=throttle,
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
        throttle: Union[BaseThrottle, List[BaseThrottle], NOT_SET_TYPE] = NOT_SET,
        response: Any = NOT_SET,
        operation_id: Optional[str] = None,
        summary: Optional[str] = None,
        description: Optional[str] = None,
        tags: Optional[List[str]] = None,
        deprecated: Optional[bool] = None,
        by_alias: Optional[bool] = None,
        exclude_unset: Optional[bool] = None,
        exclude_defaults: Optional[bool] = None,
        exclude_none: Optional[bool] = None,
        url_name: Optional[str] = None,
        include_in_schema: bool = True,
        openapi_extra: Optional[Dict[str, Any]] = None,
    ) -> Callable[[TCallable], TCallable]:
        return self.api_operation(
            ["PUT"],
            path,
            auth=auth,
            throttle=throttle,
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
        throttle: Union[BaseThrottle, List[BaseThrottle], NOT_SET_TYPE] = NOT_SET,
        response: Any = NOT_SET,
        operation_id: Optional[str] = None,
        summary: Optional[str] = None,
        description: Optional[str] = None,
        tags: Optional[List[str]] = None,
        deprecated: Optional[bool] = None,
        by_alias: Optional[bool] = None,
        exclude_unset: Optional[bool] = None,
        exclude_defaults: Optional[bool] = None,
        exclude_none: Optional[bool] = None,
        url_name: Optional[str] = None,
        include_in_schema: bool = True,
        openapi_extra: Optional[Dict[str, Any]] = None,
    ) -> Callable[[TCallable], TCallable]:
        def decorator(view_func: TCallable) -> TCallable:
            self.add_api_operation(
                path,
                methods,
                view_func,
                auth=auth,
                throttle=throttle,
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
            return view_func

        return decorator

    def add_api_operation(
        self,
        path: str,
        methods: List[str],
        view_func: Callable[..., Any],
        *,
        auth: Any = NOT_SET,
        throttle: Union[BaseThrottle, List[BaseThrottle], NOT_SET_TYPE] = NOT_SET,
        response: Any = NOT_SET,
        operation_id: Optional[str] = None,
        summary: Optional[str] = None,
        description: Optional[str] = None,
        tags: Optional[List[str]] = None,
        deprecated: Optional[bool] = None,
        by_alias: Optional[bool] = None,
        exclude_unset: Optional[bool] = None,
        exclude_defaults: Optional[bool] = None,
        exclude_none: Optional[bool] = None,
        url_name: Optional[str] = None,
        include_in_schema: bool = True,
        openapi_extra: Optional[Dict[str, Any]] = None,
    ) -> None:
        self._check_not_frozen()
        path = _keep_uuid_as_string(path)

        # No decoration here - will be done in build_routers

        if path not in self.path_operations:
            if path not in self.websocket_operations:
                self._route_order.append(path)
            path_view = PathView()
            self.path_operations[path] = path_view
        else:
            path_view = self.path_operations[path]

        by_alias = by_alias is None and self.by_alias or by_alias
        exclude_unset = exclude_unset is None and self.exclude_unset or exclude_unset
        exclude_defaults = (
            exclude_defaults is None and self.exclude_defaults or exclude_defaults
        )
        exclude_none = exclude_none is None and self.exclude_none or exclude_none

        path_view.add_operation(
            path=path,
            methods=methods,
            view_func=view_func,
            auth=auth,
            throttle=throttle,
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
        # Note: API binding is now done via BoundRouter when urls are generated

        return None

    def websocket(
        self,
        path: str,
        *,
        auth: Any = NOT_SET,
        throttle: Union[BaseThrottle, List[BaseThrottle], NOT_SET_TYPE] = NOT_SET,
        check_origin: Optional[bool] = None,
        url_name: Optional[str] = None,
    ) -> Callable[[TCallable], TCallable]:
        """
        Register an ``async def`` websocket handler::

            @router.websocket("/ws/{room}")
            async def chat(websocket: WebSocket, room: str):
                await websocket.accept()
                ...

        ``throttle`` limits new connections (handshakes). ``check_origin``
        overrides ``settings.NINJA_WEBSOCKET_CHECK_ORIGIN`` for this route.
        """

        def decorator(view_func: TCallable) -> TCallable:
            self.add_websocket_operation(
                path,
                view_func,
                auth=auth,
                throttle=throttle,
                check_origin=check_origin,
                url_name=url_name,
            )
            return view_func

        return decorator

    def add_websocket_operation(
        self,
        path: str,
        view_func: Callable[..., Any],
        *,
        auth: Any = NOT_SET,
        throttle: Union[BaseThrottle, List[BaseThrottle], NOT_SET_TYPE] = NOT_SET,
        check_origin: Optional[bool] = None,
        url_name: Optional[str] = None,
    ) -> WebSocketOperation:
        self._check_not_frozen()
        path = _keep_uuid_as_string(path)
        if path in self.websocket_operations:
            raise ConfigError(f"WebSocket route '{path}' is already registered")
        if path not in self.path_operations:
            self._route_order.append(path)
        operation = WebSocketOperation(
            path,
            view_func,
            auth=auth,
            throttle=throttle,
            check_origin=check_origin,
            url_name=url_name,
        )
        self.websocket_operations[path] = operation
        view_func._ninja_operation = operation  # type: ignore
        return operation

    def urls_paths(
        self, prefix: str, api: Optional["NinjaAPI"] = None
    ) -> Iterator[URLPattern]:
        """
        Generate URL patterns for this router.

        Note: This method is primarily for internal use. For mounting routers to APIs,
        use NinjaAPI.add_router() which handles proper binding via BoundRouter.

        Args:
            prefix: URL prefix for all paths
            api: Optional API instance for generating URL names (for backward compat)
        """
        # Ensure decorators are applied before generating URLs
        self._apply_decorators_to_operations()

        prefix = replace_path_param_notation(prefix)
        for path, path_view in self.path_operations.items():
            for operation in path_view.operations:
                path = replace_path_param_notation(path)
                route = "/".join([i for i in (prefix, path) if i])
                # to skip lot of checks we simply treat double slash as a mistake:
                route = normalize_path(route)
                route = route.lstrip("/")

                url_name = getattr(operation, "url_name", "")
                if not url_name and api:
                    url_name = api.get_operation_url_name(operation, router=self)

                yield django_path(route, path_view.get_view(), name=url_name)

    @overload
    def webhook(self, name: TSchemaClass) -> TSchemaClass: ...

    @overload
    def webhook(
        self,
        name: Optional[str] = None,
        *,
        method: str = "POST",
        summary: Optional[str] = None,
        description: Optional[str] = None,
        tags: Optional[List[str]] = None,
        operation_id: Optional[str] = None,
        deprecated: Optional[bool] = None,
        include_in_schema: bool = True,
        openapi_extra: Optional[Dict[str, Any]] = None,
    ) -> Callable[[TSchemaClass], TSchemaClass]: ...

    def webhook(
        self,
        name: Union[str, TSchemaClass, None] = None,
        *,
        method: str = "POST",
        summary: Optional[str] = None,
        description: Optional[str] = None,
        tags: Optional[List[str]] = None,
        operation_id: Optional[str] = None,
        deprecated: Optional[bool] = None,
        include_in_schema: bool = True,
        openapi_extra: Optional[Dict[str, Any]] = None,
    ) -> Union[TSchemaClass, Callable[[TSchemaClass], TSchemaClass]]:
        """
        Register a Schema class as the payload of a webhook your API sends.
        Can be used as ``@router.webhook``, ``@router.webhook()`` or
        ``@router.webhook("order.paid")`` - name defaults to the class name.

        Webhooks are only documented (in the OpenAPI ``webhooks`` section),
        Django Ninja does not send them.
        """
        if isinstance(name, type):  # used without parentheses: @router.webhook
            return self.webhook()(name)

        def decorator(schema: TSchemaClass) -> TSchemaClass:
            self.add_webhook(
                Webhook(
                    schema,
                    name,
                    method=method,
                    summary=summary,
                    description=description,
                    tags=tags,
                    operation_id=operation_id,
                    deprecated=deprecated,
                    include_in_schema=include_in_schema,
                    openapi_extra=openapi_extra,
                )
            )
            return schema

        return decorator

    def add_webhook(self, webhook: Webhook) -> None:
        if webhook.name in self.webhooks:
            raise ConfigError(f'Webhook "{webhook.name}" is already registered')
        self.webhooks[webhook.name] = webhook

    def add_router(
        self,
        prefix: str,
        router: Union["Router", str],
        *,
        auth: Any = NOT_SET,
        throttle: Union[BaseThrottle, List[BaseThrottle], NOT_SET_TYPE] = NOT_SET,
        tags: Optional[List[str]] = None,
    ) -> None:
        self._check_not_frozen()

        if isinstance(router, str):
            router = import_string(router)
            assert isinstance(router, Router)

        # Store child router with its mount-time configuration.
        # Auth/throttle/tags overrides are kept per mount (not written to the child
        # template), so a child reused under several parents stays isolated.
        self._routers.append((prefix, router, tags))
        self._router_overrides.append((auth, throttle))

    def add_decorator(
        self,
        decorator: Callable,
        mode: DecoratorMode = "operation",
    ) -> None:
        """
        Add a decorator to be applied to all operations in this router.

        Args:
            decorator: The decorator function to apply
            mode: "operation" (default) applies after validation,
                  "view" applies before validation
        """
        self._check_not_frozen()
        if mode not in ("view", "operation"):
            raise ValueError(f"Invalid decorator mode: {mode}")
        self._decorators.append((decorator, mode))

    def build_routers(
        self,
        prefix: str,
        inherited_decorators: Optional[List[Tuple[Callable, DecoratorMode]]] = None,
        inherited_auth: Any = NOT_SET,
        inherited_throttle: Any = NOT_SET,
        inherited_tags: Optional[List[str]] = None,
        mount_auth: Any = NOT_SET,
        mount_throttle: Any = NOT_SET,
    ) -> List[RouterMount]:
        """
        Build mount configurations for this router and all child routers.

        This method does NOT mutate any router state - it returns a list of
        RouterMount objects that describe how to bind routers to an API.

        Args:
            prefix: The URL prefix for this router
            inherited_decorators: Decorators inherited from parent routers/API
            inherited_auth: Auth inherited from parent routers
            inherited_throttle: Throttle inherited from parent routers
            inherited_tags: Tags inherited from parent routers
            mount_auth: Auth override from add_router() for this mount; beats self.auth
            mount_throttle: Throttle override from add_router() for this mount

        Returns:
            List of RouterMount configurations for this router and all descendants
        """
        if inherited_decorators is None:
            inherited_decorators = []

        # Create mount configuration for this router
        mount = RouterMount(
            template=self,
            prefix=prefix,
            inherited_decorators=list(inherited_decorators),
            inherited_auth=inherited_auth,
            inherited_throttle=inherited_throttle,
            inherited_tags=inherited_tags,
        )

        # Calculate values to pass to children
        child_decorators = inherited_decorators + self._decorators

        # For auth/throttle/tags, effective value is used for children:
        # priority: mount override > this router's own setting > inherited
        child_auth = next(
            (a for a in (mount_auth, self.auth) if a is not NOT_SET), inherited_auth
        )
        child_throttle = next(
            (t for t in (mount_throttle, self.throttle) if t is not NOT_SET),
            inherited_throttle,
        )
        child_tags = self.tags if self.tags is not None else inherited_tags

        # Build mounts for child routers
        child_mounts: List[RouterMount] = []
        for (child_prefix, child_router, child_mount_tags), (
            child_mount_auth,
            child_mount_throttle,
        ) in zip(self._routers, self._router_overrides):
            child_path = normalize_path("/".join((prefix, child_prefix))).lstrip("/")
            mounts = child_router.build_routers(
                child_path,
                child_decorators,
                child_auth,
                child_throttle,
                child_tags,
                mount_auth=child_mount_auth,
                mount_throttle=child_mount_throttle,
            )
            # Apply mount-level overrides to the first mount (the child router itself)
            if child_mount_auth is not NOT_SET:
                mounts[0].auth = child_mount_auth
            if child_mount_throttle is not NOT_SET:
                mounts[0].throttle = child_mount_throttle
            if child_mount_tags is not None:
                mounts[0].tags = child_mount_tags
            child_mounts.extend(mounts)

        return [mount, *child_mounts]

    def _apply_decorators_to_operations(self) -> None:
        """Apply all stored decorators to operations in this router"""
        for path_view in self.path_operations.values():
            for operation in path_view.operations:
                # Track what decorators have already been applied to avoid duplicates
                applied_decorators = getattr(operation, "_applied_decorators", [])

                # Apply decorators that haven't been applied yet
                for decorator, mode in self._decorators:
                    if (decorator, mode) not in applied_decorators:
                        if mode == "view":
                            operation.run = decorator(operation.run)  # type: ignore
                        elif mode == "operation":
                            operation.view_func = decorator(operation.view_func)
                        else:
                            raise ValueError(
                                f"Invalid decorator mode: {mode}"
                            )  # pragma: no cover
                        applied_decorators.append((decorator, mode))

                # Store what decorators have been applied
                operation._applied_decorators = applied_decorators  # type: ignore[attr-defined]
