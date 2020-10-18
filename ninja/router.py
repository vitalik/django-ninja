from collections import OrderedDict
from typing import Callable, List

from django.http import HttpResponseNotAllowed
from django.urls import path as django_path
from ninja.operation import Operation, PathView
from ninja.constants import NOT_SET
from ninja.utils import normalize_path


class Router:
    def __init__(self):
        self.operations = OrderedDict()  # TODO: better rename to path_operations
        self.api = None

    def get(self, path: str, *, auth=NOT_SET, response=None):
        return self.api_operation(["GET"], path, auth=auth, response=response)

    def post(self, path: str, *, auth=NOT_SET, response=None):
        return self.api_operation(["POST"], path, auth=auth, response=response)

    def delete(self, path: str, *, auth=NOT_SET, response=None):
        return self.api_operation(["DELETE"], path, auth=auth, response=response)

    def patch(self, path: str, *, auth=NOT_SET, response=None):
        return self.api_operation(["PATCH"], path, auth=auth, response=response)

    def put(self, path: str, *, auth=NOT_SET, response=None):
        return self.api_operation(["PUT"], path, auth=auth, response=response)

    def api_operation(
        self, methods: List[str], path: str, *, auth=NOT_SET, response=None
    ):
        def decorator(view_func):
            self.add_api_operation(
                path, methods, view_func, auth=auth, response=response
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
        response=None
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
        )
        if self.api:
            path_view.set_api_instance(self.api)

    def set_api_instance(self, api):
        self.api = api
        for path_view in self.operations.values():
            path_view.set_api_instance(self.api)

    def urls_paths(self, prefix: str):
        for path, path_view in self.operations.items():
            path = path.replace("{", "<").replace("}", ">")
            route = "/".join([i for i in (prefix, path) if i])
            # to skip lot of checks we simply treat double slash as a mistake:
            route = normalize_path(route)
            route = route.lstrip("/")

            yield django_path(route, path_view.get_view())
