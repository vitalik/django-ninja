import pydantic
import django
from django.http import HttpResponse, HttpResponseNotAllowed
from typing import Callable, List, Any, Union, Optional, Sequence
from ninja.responses import Response
from ninja.errors import InvalidInput
from ninja.constants import NOT_SET
from ninja.schema import Schema
from ninja.signature import ViewSignature, is_async


class Operation:
    def __init__(
        self,
        path: str,
        methods: List[str],
        view_func: Callable,
        *,
        auth: Optional[Union[Sequence[Callable], Callable, object]] = NOT_SET,
        response: Any = None,
    ):
        self.is_async = False
        self.path = path
        self.methods = methods
        self.view_func = view_func
        self.auth: Sequence[Callable] = []
        if auth is not None and auth is not NOT_SET:
            self.auth = isinstance(auth, Sequence) and auth or [auth]

        self.signature = ViewSignature(self.path, self.view_func)
        self.models = self.signature.models
        self.response_model = self._create_response_model(response)

    def run(self, request, **kw):
        unauthorized = self._run_authentication(request)
        if unauthorized:
            return unauthorized

        values, errors = self._get_values(request, kw)
        if errors:
            return Response({"detail": errors}, status=422)
        result = self.view_func(request, **values)
        return self._create_response(result)

    def _run_authentication(self, request):
        if not self.auth:
            return
        for callback in self.auth:
            result = callback(request)
            if result is not None:
                request.auth = result
                return
        return Response({"detail": "Unauthorized"}, status=401)

    def _create_response(self, result: Any):
        if isinstance(result, HttpResponse):
            return result
        if self.response_model is None:
            return Response(result)

        result = self.response_model(response=result).dict()["response"]
        return Response(result)

    def _get_values(self, request, path_params):
        values, errors = {}, []
        for model in self.models:
            try:
                data = model.resolve(request, path_params)
                values.update(data)
            except (pydantic.ValidationError, InvalidInput) as e:
                items = []
                for i in e.errors():
                    i["loc"] = (model._in,) + i["loc"]
                    items.append(i)
                errors.extend(items)
        return values, errors

    def _create_response_model(self, response_param):
        if response_param is None:
            return
        attrs = {"__annotations__": {"response": response_param}}
        return type("Response", (Schema,), attrs)


class AsyncOperation(Operation):
    def __init__(self, *args, **kwargs):
        if django.VERSION < (3, 1):
            raise Exception("Async operations are supported only with Django 3.1+")
        super().__init__(*args, **kwargs)
        self.is_async = True

    async def run(self, request, **kw):
        unauthorized = self._run_authentication(request)
        if unauthorized:
            return unauthorized

        values, errors = self._get_values(request, kw)
        if errors:
            return Response({"detail": errors}, status=422)
        result = await self.view_func(request, **values)
        return self._create_response(result)


class PathView:
    def __init__(self):
        self.operations = []
        self.is_async = False  # if at least one operation is async - will become True

    def append(
        self,
        path: str,
        methods: List[str],
        view_func: Callable,
        *,
        auth: Optional[Union[Sequence[Callable], Callable, object]] = NOT_SET,
        response=None,
    ):
        if is_async(view_func):
            self.is_async = True
            operation = AsyncOperation(
                path, methods, view_func, auth=auth, response=response
            )
        else:
            operation = Operation(
                path, methods, view_func, auth=auth, response=response
            )

        self.operations.append(operation)

    def get_view(self):
        if self.is_async:
            view = self._async_view
        else:
            view = self._sync_view
        view.__func__.csrf_exempt = True
        # TODO:   ^ this should probably be configurable in settings or Ninja app
        return view

    def _sync_view(self, request, *a, **kw):
        operation, error = self._find_operation(request)
        if error:
            return error
        return operation.run(request, *a, **kw)

    async def _async_view(self, request, *a, **kw):
        from asgiref.sync import sync_to_async

        operation, error = self._find_operation(request)
        if error:
            return error
        if operation.is_async:
            return await operation.run(request, *a, **kw)
        else:
            return await sync_to_async(operation.run)(request, *a, **kw)

    def _find_operation(self, request):
        allowed_methods = set()
        for op in self.operations:
            allowed_methods.update(op.methods)
            if request.method in op.methods:
                return op, None
        return (
            None,
            HttpResponseNotAllowed(allowed_methods, content=b"Method not allowed"),
        )
