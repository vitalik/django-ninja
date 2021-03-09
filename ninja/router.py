from collections import OrderedDict
from typing import Callable, List, Optional, Tuple

from django.http import HttpResponseNotAllowed
from django.urls import path as django_path

from ninja.constants import NOT_SET
from ninja.operation import Operation, PathView
from ninja.utils import normalize_path


class Router:
    def __init__(self):
        self.operations = OrderedDict()  # TODO: better rename to path_operations
        self.api = None
        self._routers: List[Tuple[str, Router]] = []

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
        by_alias: bool = False,
        exclude_unset: bool = False,
        exclude_defaults: bool = False,
        exclude_none: bool = False,
    ):
        return self.api_operation(
            ["GET"],
            path,
            auth=auth,
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
        by_alias: bool = False,
        exclude_unset: bool = False,
        exclude_defaults: bool = False,
        exclude_none: bool = False,
    ):
        return self.api_operation(
            ["POST"],
            path,
            auth=auth,
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
        by_alias: bool = False,
        exclude_unset: bool = False,
        exclude_defaults: bool = False,
        exclude_none: bool = False,
    ):
        return self.api_operation(
            ["DELETE"],
            path,
            auth=auth,
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
        by_alias: bool = False,
        exclude_unset: bool = False,
        exclude_defaults: bool = False,
        exclude_none: bool = False,
    ):
        return self.api_operation(
            ["PATCH"],
            path,
            auth=auth,
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
        by_alias: bool = False,
        exclude_unset: bool = False,
        exclude_defaults: bool = False,
        exclude_none: bool = False,
    ):
        return self.api_operation(
            ["PUT"],
            path,
            auth=auth,
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
        by_alias: bool = False,
        exclude_unset: bool = False,
        exclude_defaults: bool = False,
        exclude_none: bool = False,
    ):
        def decorator(view_func):
            self.add_api_operation(
                path,
                methods,
                view_func,
                auth=auth,
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
            )
            return view_func

        return decorator

    def add_api_operation(
        self,
        path: str,
        methods: List[str],
        view_func: Callable,
        *,
        auth=NOT_SET,
        response=None,
        operation_id: Optional[str] = None,
        summary: Optional[str] = None,
        description: Optional[str] = None,
        tags: Optional[List[str]] = None,
        deprecated: Optional[bool] = None,
        by_alias: bool = False,
        exclude_unset: bool = False,
        exclude_defaults: bool = False,
        exclude_none: bool = False,
    ):
        if path not in self.operations:
            path_view = PathView()
            self.operations[path] = path_view
        else:
            path_view = self.operations[path]
        path_view.add(
            path=path,
            methods=methods,
            view_func=view_func,
            auth=auth,
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
        )
        if self.api:
            path_view.set_api_instance(self.api)

    def set_api_instance(self, api):
        self.api = api
        for path_view in self.operations.values():
            path_view.set_api_instance(self.api)
        for _, router in self._routers:
            router.set_api_instance(api)

    def urls_paths(self, prefix: str):
        for path, path_view in self.operations.items():
            path = path.replace("{", "<").replace("}", ">")
            route = "/".join([i for i in (prefix, path) if i])
            # to skip lot of checks we simply treat double slash as a mistake:
            route = normalize_path(route)
            route = route.lstrip("/")

            yield django_path(route, path_view.get_view())

    def add_router(self, prefix, router):
        self._routers.append((prefix, router))

    def build_routers(self, prefix):
        internal_routes = []
        for inter_prefix, inter_router in self._routers:
            _route = normalize_path("/".join((prefix, inter_prefix))).lstrip("/")
            internal_routes.extend(inter_router.build_routers(_route))

        return [(prefix, self), *internal_routes]
