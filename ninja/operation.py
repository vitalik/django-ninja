from typing import (
    TYPE_CHECKING,
    Any,
    Callable,
    Dict,
    Iterable,
    List,
    Optional,
    Sequence,
    Tuple,
    Type,
    Union,
    cast,
)

import django
import pydantic
from django.http import HttpRequest, HttpResponse, HttpResponseNotAllowed

from ninja.constants import NOT_SET
from ninja.errors import ConfigError, ValidationError
from ninja.schema import Schema
from ninja.signature import ViewSignature, is_async
from ninja.types import DictStrAny
from ninja.utils import check_csrf

if TYPE_CHECKING:
    from ninja import NinjaAPI  # pragma: no cover

__all__ = ["Operation", "PathView", "ResponseObject"]


class Operation:
    def __init__(
        self,
        path: str,
        methods: List[str],
        view_func: Callable,
        *,
        auth: Optional[Union[Sequence[Callable], Callable, object]] = NOT_SET,
        response: Any = None,
        operation_id: Optional[str] = None,
        summary: Optional[str] = None,
        description: Optional[str] = None,
        tags: Optional[List[str]] = None,
        deprecated: Optional[bool] = None,
        by_alias: bool = False,
        exclude_unset: bool = False,
        exclude_defaults: bool = False,
        exclude_none: bool = False,
    ) -> None:
        self.is_async = False
        self.path: str = path
        self.methods: List[str] = methods
        self.view_func: Callable = view_func
        self.api: "NinjaAPI" = cast("NinjaAPI", None)

        self.auth_param: Optional[Union[Sequence[Callable], Callable, object]] = auth
        self.auth_callbacks: Sequence[Callable] = []
        self._set_auth(auth)

        self.signature = ViewSignature(self.path, self.view_func)
        self.models = self.signature.models

        self.response_model: Any
        if isinstance(response, dict):
            self.response_model = self._create_response_model_multiple(response)
        else:
            self.response_model = self._create_response_model(response)

        self.operation_id = operation_id
        self.summary = summary or self.view_func.__name__.title().replace("_", " ")
        self.description = description or self.signature.docstring
        self.tags = tags
        self.deprecated = deprecated

        # Exporting models params
        self.by_alias = by_alias
        self.exclude_unset = exclude_unset
        self.exclude_defaults = exclude_defaults
        self.exclude_none = exclude_none

    def run(self, request: HttpRequest, **kw: Any) -> HttpResponse:
        error = self._run_checks(request)
        if error:
            return error
        try:
            values = self._get_values(request, kw)
            result = self.view_func(request, **values)
            return self._result_to_response(request, result)
        except Exception as e:
            return self.api.on_exception(request, e)

    def set_api_instance(self, api: "NinjaAPI") -> None:
        self.api = api
        if self.auth_param == NOT_SET and api.auth != NOT_SET:
            # if api instance have auth and operation not - then we set auth from api instance
            self._set_auth(self.api.auth)

    def _set_auth(
        self, auth: Optional[Union[Sequence[Callable], Callable, object]]
    ) -> None:
        if auth is not None and auth is not NOT_SET:
            self.auth_callbacks = isinstance(auth, Sequence) and auth or [auth]  # type: ignore

    def _run_checks(self, request: HttpRequest) -> Optional[HttpResponse]:
        "Runs security checks for each operation"
        # auth:
        if self.auth_callbacks:
            error = self._run_authentication(request)
            if error:
                return error

        # csrf:
        if self.api.csrf:
            error = check_csrf(request, self.view_func)
            if error:
                return error

        return None

    def _run_authentication(self, request: HttpRequest) -> Optional[HttpResponse]:
        for callback in self.auth_callbacks:
            result = callback(request)
            if result is not None:
                request.auth = result  # type: ignore
                return None
        return self.api.create_response(request, {"detail": "Unauthorized"}, status=401)

    def _result_to_response(self, request: HttpRequest, result: Any) -> HttpResponse:
        if isinstance(result, HttpResponse):
            return result
        if self.response_model is None:
            return self.api.create_response(request, result)

        status = 200
        response_model = self.response_model
        if isinstance(result, tuple) and len(result) == 2:
            status = result[0]
            result = result[1]
        if isinstance(response_model, dict):
            if status in response_model:
                response_model = response_model[status]
            elif Ellipsis in response_model:
                response_model = response_model[Ellipsis]
            else:
                raise ConfigError(
                    f"Schema for status {status} is not set in response {response_model.keys()}"
                )

        resp_object = ResponseObject(result)
        # ^ we need object because getter_dict seems work only with from_orm
        result = response_model.from_orm(resp_object).dict(
            by_alias=self.by_alias,
            exclude_unset=self.exclude_unset,
            exclude_defaults=self.exclude_defaults,
            exclude_none=self.exclude_none,
        )["response"]
        return self.api.create_response(request, result, status=status)

    def _get_values(self, request: HttpRequest, path_params: Any) -> DictStrAny:
        values, errors = {}, []
        for model in self.models:
            try:
                data = model.resolve(request, self.api, path_params)
                values.update(data)
            except pydantic.ValidationError as e:
                items = []
                for i in e.errors():
                    i["loc"] = (model._in,) + i["loc"]
                    items.append(i)
                errors.extend(items)
        if errors:
            raise ValidationError(errors)
        return values

    def _create_response_model_multiple(
        self, response_param: DictStrAny
    ) -> Dict[str, Optional[Type[Schema]]]:
        result = {}
        for key, model in response_param.items():
            status_codes = isinstance(key, Iterable) and key or [key]
            for code in status_codes:
                result[code] = self._create_response_model(model)
        return result

    def _create_response_model(self, response_param: Any) -> Optional[Type[Schema]]:
        if response_param is None:
            return None
        attrs = {"__annotations__": {"response": response_param}}
        return type("NinjaResponseSchema", (Schema,), attrs)


class AsyncOperation(Operation):
    def __init__(self, *args: Any, **kwargs: Any) -> None:
        if django.VERSION < (3, 1):  # pragma: no cover
            raise Exception("Async operations are supported only with Django 3.1+")
        super().__init__(*args, **kwargs)
        self.is_async = True

    async def run(self, request: HttpRequest, **kw: Any) -> HttpResponse:  # type: ignore
        error = self._run_checks(request)
        if error:
            return error
        try:
            values = self._get_values(request, kw)
            result = await self.view_func(request, **values)
            return self._result_to_response(request, result)
        except Exception as e:
            return self.api.on_exception(request, e)


class PathView:
    def __init__(self) -> None:
        self.operations: List[Operation] = []
        self.is_async = False  # if at least one operation is async - will become True
        self.url_name: Optional[str] = None

    def add_operation(
        self,
        path: str,
        methods: List[str],
        view_func: Callable,
        *,
        auth: Optional[Union[Sequence[Callable], Callable, object]] = NOT_SET,
        response: Any = None,
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
    ) -> Operation:
        if url_name:
            self.url_name = url_name

        OperationClass = Operation
        if is_async(view_func):
            self.is_async = True
            OperationClass = AsyncOperation

        operation = OperationClass(
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

        self.operations.append(operation)
        return operation

    def set_api_instance(self, api: "NinjaAPI") -> None:
        self.api = api
        for op in self.operations:
            op.set_api_instance(api)

    def get_view(self) -> Callable:
        view: Callable
        if self.is_async:
            view = self._async_view
        else:
            view = self._sync_view

        view.__func__.csrf_exempt = True  # type: ignore
        return view

    def _sync_view(self, request: HttpRequest, *a: Any, **kw: Any) -> HttpResponse:
        operation, error = self._find_operation(request)
        if error:
            return error
        return operation.run(request, *a, **kw)  # type: ignore

    async def _async_view(
        self, request: HttpRequest, *a: Any, **kw: Any
    ) -> HttpResponse:
        from asgiref.sync import sync_to_async

        operation, error = self._find_operation(request)
        if error:
            return error
        if operation.is_async:
            return await operation.run(request, *a, **kw)  # type: ignore
        else:
            return await sync_to_async(operation.run)(request, *a, **kw)  # type: ignore

    def _find_operation(
        self, request: HttpRequest
    ) -> Tuple[Any, Optional[HttpResponse]]:
        allowed_methods = set()
        for op in self.operations:
            allowed_methods.update(op.methods)
            if request.method in op.methods:
                return op, None
        return (
            None,
            HttpResponseNotAllowed(allowed_methods, content=b"Method not allowed"),
        )


class ResponseObject:
    "Basically this is just a helper to be able to pass response to pydantic's from_orm"

    def __init__(self, response: HttpResponse) -> None:
        self.response = response
