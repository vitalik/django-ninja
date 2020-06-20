from collections import OrderedDict
from typing import Callable, List

from django.http import HttpResponseNotAllowed
from django.urls import path as django_path
from ninja.operation import Operation
from ninja.constants import NOT_SET


class Router:
    def __init__(self):
        self.operations = OrderedDict()

    def get(self, path: str, *, auth=NOT_SET):
        return self.api_operation(["GET"], path, auth=auth)

    def post(self, path: str, *, auth=NOT_SET):
        return self.api_operation(["POST"], path, auth=auth)

    def delete(self, path: str, *, auth=NOT_SET):
        return self.api_operation(["DELETE"], path, auth=auth)

    def patch(self, path: str, *, auth=NOT_SET):
        return self.api_operation(["PATCH"], path, auth=auth)

    def put(self, path: str, *, auth=NOT_SET):
        return self.api_operation(["PUT"], path, auth=auth)

    def api_operation(self, methods: List[str], path: str, *, auth=NOT_SET):
        def decorator(view_func):
            self.add_api_operation(path, methods, view_func, auth=auth)
            return view_func

        return decorator

    def add_api_operation(
        self, path: str, methods: List[str], view_func: Callable, *, auth=NOT_SET
    ):
        op = Operation(path=path, methods=methods, view_func=view_func, auth=auth)
        if path not in self.operations:
            self.operations[path] = []
        self.operations[path].append(op)

    def urls_paths(self, prefix: str):
        for ep_path, ep_list in self.operations.items():
            ep_path = ep_path.replace("{", "<").replace("}", ">")
            route = "/".join([i for i in (prefix, ep_path) if i])
            # to skip lot of checks we simply treat doulbe slash as a mistake:
            route = route.replace("//", "/")
            route = route.lstrip("/")
            yield django_path(route, self._operation_view(ep_list))

    def _operation_view(self, operations: List[Operation]):
        def wrapper(request, *a, **kw):
            allowed_methods = set()
            for ep in operations:
                allowed_methods.update(ep.methods)
                if request.method in ep.methods:
                    return ep.run(request, *a, **kw)
            return HttpResponseNotAllowed(
                allowed_methods, content=b"Method not allowed"
            )

        wrapper.csrf_exempt = True
        # TODO:   ^ this should probably be configurable in settings or Ninja app
        return wrapper
