import re
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
)

from django.urls import URLPattern
from django.urls import path as django_path
from django.utils.module_loading import import_string

from ninja.constants import NOT_SET, NOT_SET_TYPE
from ninja.decorators import DecoratorMode
from ninja.errors import ConfigError
from ninja.operation import PathView
from ninja.throttling import BaseThrottle
from ninja.types import TCallable
from ninja.utils import normalize_path, replace_path_param_notation

if TYPE_CHECKING:
    from ninja import NinjaAPI  # pragma: no cover


__all__ = ["Router", "RouterMount", "BoundRouter"]


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

        if mount.tags is not None:
            self.tags = mount.tags
        elif mount.template.tags is not None:
            self.tags = mount.template.tags
        elif mount.inherited_tags is not None:
            self.tags = mount.inherited_tags
        else:
            self.tags = None

        # Clone operations and apply decorators
        self.path_operations: Dict[str, PathView] = {}
        self._bind_operations()

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
                    if self.api.throttle != NOT_SET:
                        throttle = self.api.throttle
                        operation.throttle_objects = (
                            isinstance(throttle, BaseThrottle)
                            and [throttle]
                            or throttle  # type: ignore
                        )
                    if self.throttle != NOT_SET:
                        throttle = self.throttle
                        operation.throttle_objects = (
                            isinstance(throttle, BaseThrottle)
                            and [throttle]
                            or throttle  # type: ignore
                        )

                # Apply tags inheritance
                if operation.tags is None and self.tags is not None:
                    operation.tags = self.tags

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
        """Generate URL patterns for this bound router."""
        prefix = replace_path_param_notation(prefix)
        for path, path_view in self.path_operations.items():
            path = replace_path_param_notation(path)
            route = "/".join([i for i in (prefix, path) if i])
            route = normalize_path(route)
            route = route.lstrip("/")

            for operation in path_view.operations:
                url_name = getattr(operation, "url_name", "")
                if not url_name:
                    url_name = self.api.get_operation_url_name(
                        operation, router=self.template
                    )
                    # Apply url_name_prefix if specified
                    if self.url_name_prefix and url_name:
                        url_name = f"{self.url_name_prefix}_{url_name}"

                yield django_path(route, path_view.get_view(), name=url_name)


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
        self._routers: List[Tuple[str, Router]] = []
        self._decorators: List[Tuple[Callable, DecoratorMode]] = []

    def _freeze(self) -> None:
        """Mark router as frozen - no more modifications allowed."""
        self._frozen = True
        for _, child_router in self._routers:
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
        view_func: Callable,
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
        path = re.sub(r"\{uuid:(\w+)\}", r"{uuidstr:\1}", path, flags=re.IGNORECASE)
        # django by default convert strings to UUIDs
        # but we want to keep them as strings to let pydantic handle conversion/validation
        # if user whants UUID object
        # uuidstr is custom registered converter

        # No decoration here - will be done in build_routers

        if path not in self.path_operations:
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

    def urls_paths(self, prefix: str, api: Optional["NinjaAPI"] = None) -> Iterator[URLPattern]:
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

        # Store child router with its configuration
        # Auth/throttle/tags are stored on the child router for now,
        # but the actual binding happens via RouterMount during URL generation
        if auth != NOT_SET:
            router.auth = auth
        if throttle != NOT_SET:
            router.throttle = throttle
        if tags is not None:
            router.tags = tags
        self._routers.append((prefix, router))

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
        # priority: this router's own setting > inherited
        child_auth = self.auth if self.auth is not NOT_SET else inherited_auth
        child_throttle = self.throttle if self.throttle is not NOT_SET else inherited_throttle
        child_tags = self.tags if self.tags is not None else inherited_tags

        # Build mounts for child routers
        child_mounts: List[RouterMount] = []
        for child_prefix, child_router in self._routers:
            child_path = normalize_path("/".join((prefix, child_prefix))).lstrip("/")
            child_mounts.extend(child_router.build_routers(
                child_path,
                child_decorators,
                child_auth,
                child_throttle,
                child_tags,
            ))

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
