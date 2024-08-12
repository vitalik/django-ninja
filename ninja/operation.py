from typing import (
    TYPE_CHECKING,
    Any,
    Callable,
    Coroutine,
    Dict,
    Iterable,
    List,
    Optional,
    Sequence,
    Type,
    Union,
    cast,
)

import pydantic
from asgiref.sync import async_to_sync
from django.http import HttpRequest, HttpResponse, HttpResponseNotAllowed
from django.http.response import HttpResponseBase

from ninja.constants import NOT_SET, NOT_SET_TYPE
from ninja.errors import AuthenticationError, ConfigError, Throttled, ValidationError
from ninja.params.models import TModels
from ninja.schema import Schema, pydantic_version
from ninja.signature import ViewSignature, is_async
from ninja.throttling import BaseThrottle
from ninja.types import DictStrAny
from ninja.utils import check_csrf, is_async_callable

if TYPE_CHECKING:
    from ninja import NinjaAPI, Router  # pragma: no cover

__all__ = ["Operation", "PathView", "ResponseObject"]


class Operation:
    def __init__(
        self,
        path: str,
        methods: List[str],
        view_func: Callable,
        *,
        auth: Optional[Union[Sequence[Callable], Callable, NOT_SET_TYPE]] = NOT_SET,
        throttle: Union[BaseThrottle, List[BaseThrottle], NOT_SET_TYPE] = NOT_SET,
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
        include_in_schema: bool = True,
        url_name: Optional[str] = None,
        openapi_extra: Optional[Dict[str, Any]] = None,
    ) -> None:
        self.is_async = False
        self.path: str = path
        self.methods: List[str] = methods
        self.view_func: Callable = view_func
        self.api: NinjaAPI = cast("NinjaAPI", None)
        if url_name is not None:
            self.url_name = url_name

        self.auth_param: Optional[Union[Sequence[Callable], Callable, object]] = auth
        self.auth_callbacks: Sequence[Callable] = []
        self._set_auth(auth)

        if isinstance(throttle, BaseThrottle):
            throttle = [throttle]
        self.throttle_param = throttle
        self.throttle_objects: List[BaseThrottle] = []
        if throttle is not NOT_SET:
            for th in throttle:  # type: ignore
                assert isinstance(
                    th, BaseThrottle
                ), "Throttle should be an instance of BaseThrottle"
                self.throttle_objects.append(th)

        self.signature = ViewSignature(self.path, self.view_func)
        self.models: TModels = self.signature.models

        self.response_models: Dict[Any, Any]
        if response is NOT_SET:
            self.response_models = {200: NOT_SET}
        elif isinstance(response, dict):
            self.response_models = self._create_response_model_multiple(response)
        else:
            self.response_models = {200: self._create_response_model(response)}

        self.operation_id = operation_id
        self.summary = summary or self.view_func.__name__.title().replace("_", " ")
        self.description = description or self.signature.docstring
        self.tags = tags
        self.deprecated = deprecated
        self.include_in_schema = include_in_schema
        self.openapi_extra = openapi_extra

        # Exporting models params
        self.by_alias = by_alias
        self.exclude_unset = exclude_unset
        self.exclude_defaults = exclude_defaults
        self.exclude_none = exclude_none

        if hasattr(view_func, "_ninja_contribute_to_operation"):
            # Allow 3rd party code to contribute to the operation behavior
            callbacks: List[Callable] = view_func._ninja_contribute_to_operation
            for callback in callbacks:
                callback(self)

    def run(self, request: HttpRequest, **kw: Any) -> HttpResponseBase:
        error = self._run_checks(request)
        if error:
            return error
        try:
            temporal_response = self.api.create_temporal_response(request)
            values = self._get_values(request, kw, temporal_response)
            result = self.view_func(request, **values)
            return self._result_to_response(request, result, temporal_response)
        except Exception as e:
            if isinstance(e, TypeError) and "required positional argument" in str(e):
                msg = "Did you fail to use functools.wraps() in a decorator?"
                msg = f"{e.args[0]}: {msg}" if e.args else msg
                e.args = (msg,) + e.args[1:]
            return self.api.on_exception(request, e)

    def set_api_instance(self, api: "NinjaAPI", router: "Router") -> None:
        self.api = api

        if self.auth_param == NOT_SET:
            if api.auth != NOT_SET:
                self._set_auth(self.api.auth)
            if router.auth != NOT_SET:
                self._set_auth(router.auth)

        if self.throttle_param == NOT_SET:
            if api.throttle != NOT_SET:
                self.throttle_objects = (
                    isinstance(api.throttle, BaseThrottle)
                    and [api.throttle]
                    or api.throttle  # type: ignore
                )
            if router.throttle != NOT_SET:
                _t = router.throttle
                self.throttle_objects = isinstance(_t, BaseThrottle) and [_t] or _t  # type: ignore
            assert all(
                isinstance(th, BaseThrottle) for th in self.throttle_objects
            ), "Throttle should be an instance of BaseThrottle"

        if self.tags is None:
            if router.tags is not None:
                self.tags = router.tags

    def _set_auth(
        self, auth: Optional[Union[Sequence[Callable], Callable, object]]
    ) -> None:
        if auth is not None and auth is not NOT_SET:  # TODO: can it even happen ?
            self.auth_callbacks = isinstance(auth, Sequence) and auth or [auth]

    def _run_checks(self, request: HttpRequest) -> Optional[HttpResponse]:
        "Runs security/throttle checks for each operation"
        # NOTE: if you change anything in this function - do this also in AsyncOperation

        # csrf:
        if self.api.csrf:
            error = check_csrf(request, self.view_func)
            if error:
                return error

        # auth:
        if self.auth_callbacks:
            error = self._run_authentication(request)  # type: ignore
            if error:
                return error

        # Throttling:
        if self.throttle_objects:
            error = self._check_throttles(request)  # type: ignore
            if error:
                return error

        return None

    def _run_authentication(self, request: HttpRequest) -> Optional[HttpResponse]:
        for callback in self.auth_callbacks:
            try:
                if is_async_callable(callback) or getattr(callback, "is_async", False):
                    result = async_to_sync(callback)(request)
                else:
                    result = callback(request)
            except Exception as exc:
                return self.api.on_exception(request, exc)

            if result:
                request.auth = result  # type: ignore
                return None
        return self.api.on_exception(request, AuthenticationError())

    def _check_throttles(self, request: HttpRequest) -> Optional[HttpResponse]:
        throttle_durations = []
        for throttle in self.throttle_objects:
            if not throttle.allow_request(request):
                throttle_durations.append(throttle.wait())

        if throttle_durations:
            # Filter out `None` values which may happen in case of config / rate
            durations = [
                duration for duration in throttle_durations if duration is not None
            ]

            duration = max(durations, default=None)
            return self.api.on_exception(request, Throttled(wait=duration))  # type: ignore
        return None

    def _result_to_response(
        self, request: HttpRequest, result: Any, temporal_response: HttpResponse
    ) -> HttpResponseBase:
        """
        The protocol for results
         - if HttpResponse - returns as is
         - if tuple with 2 elements - means http_code + body
         - otherwise it's a body
        """
        if isinstance(result, HttpResponseBase):
            return result

        status: int = 200
        if len(self.response_models) == 1:
            status = next(iter(self.response_models))

        if isinstance(result, tuple) and len(result) == 2:
            status = result[0]
            result = result[1]

        if status in self.response_models:
            response_model = self.response_models[status]
        elif Ellipsis in self.response_models:
            response_model = self.response_models[Ellipsis]
        else:
            raise ConfigError(
                f"Schema for status {status} is not set in response"
                f" {self.response_models.keys()}"
            )

        temporal_response.status_code = status

        if response_model is NOT_SET:
            return self.api.create_response(
                request, result, temporal_response=temporal_response
            )

        if response_model is None:
            # Empty response.
            return temporal_response

        resp_object = ResponseObject(result)
        # ^ we need object because getter_dict seems work only with model_validate
        validated_object = response_model.model_validate(
            resp_object, context={"request": request, "response_status": status}
        )

        model_dump_kwargs: Dict[str, Any] = {}
        if pydantic_version >= [2, 7]:
            # pydantic added support for serialization context at 2.7
            model_dump_kwargs.update(
                context={"request": request, "response_status": status}
            )

        result = validated_object.model_dump(
            by_alias=self.by_alias,
            exclude_unset=self.exclude_unset,
            exclude_defaults=self.exclude_defaults,
            exclude_none=self.exclude_none,
            **model_dump_kwargs,
        )["response"]
        return self.api.create_response(
            request, result, temporal_response=temporal_response
        )

    def _get_values(
        self, request: HttpRequest, path_params: Any, temporal_response: HttpResponse
    ) -> DictStrAny:
        values, errors = {}, []
        for model in self.models:
            try:
                data = model.resolve(request, self.api, path_params)
                values.update(data)
            except pydantic.ValidationError as e:
                items = []
                for i in e.errors(include_url=False):
                    i["loc"] = (
                        model.__ninja_param_source__,
                    ) + model.__ninja_flatten_map_reverse__.get(i["loc"], i["loc"])
                    # removing pydantic hints
                    del i["input"]  # type: ignore
                    if (
                        "ctx" in i
                        and "error" in i["ctx"]
                        and isinstance(i["ctx"]["error"], Exception)
                    ):
                        i["ctx"]["error"] = str(i["ctx"]["error"])
                    items.append(dict(i))
                errors.extend(items)
        if errors:
            raise ValidationError(errors)
        if self.signature.response_arg:
            values[self.signature.response_arg] = temporal_response
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
        super().__init__(*args, **kwargs)
        self.is_async = True

    async def run(self, request: HttpRequest, **kw: Any) -> HttpResponseBase:  # type: ignore
        error = await self._run_checks(request)
        if error:
            return error
        try:
            temporal_response = self.api.create_temporal_response(request)
            values = self._get_values(request, kw, temporal_response)
            result = await self.view_func(request, **values)
            return self._result_to_response(request, result, temporal_response)
        except Exception as e:
            return self.api.on_exception(request, e)

    async def _run_checks(self, request: HttpRequest) -> Optional[HttpResponse]:  # type: ignore
        "Runs security checks for each operation"
        # NOTE: if you change anything in this function - do this also in Sync Operation

        # auth:
        if self.auth_callbacks:
            error = await self._run_authentication(request)
            if error:
                return error

        # csrf:
        if self.api.csrf:
            error = check_csrf(request, self.view_func)
            if error:
                return error

        # Throttling:
        if self.throttle_objects:
            error = self._check_throttles(request)
            if error:
                return error

        return None

    async def _run_authentication(self, request: HttpRequest) -> Optional[HttpResponse]:  # type: ignore
        for callback in self.auth_callbacks:
            try:
                if is_async_callable(callback) or getattr(callback, "is_async", False):
                    cor: Optional[Coroutine] = callback(request)
                    if cor is None:
                        result = None
                    else:
                        result = await cor
                else:
                    result = callback(request)
            except Exception as exc:
                return self.api.on_exception(request, exc)

            if result:
                request.auth = result  # type: ignore
                return None
        return self.api.on_exception(request, AuthenticationError())


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
        auth: Optional[Union[Sequence[Callable], Callable, NOT_SET_TYPE]] = NOT_SET,
        throttle: Union[BaseThrottle, List[BaseThrottle], NOT_SET_TYPE] = NOT_SET,
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
            include_in_schema=include_in_schema,
            url_name=url_name,
            openapi_extra=openapi_extra,
        )

        self.operations.append(operation)
        view_func._ninja_operation = operation  # type: ignore
        return operation

    def set_api_instance(self, api: "NinjaAPI", router: "Router") -> None:
        self.api = api
        for op in self.operations:
            op.set_api_instance(api, router)

    def get_view(self) -> Callable:
        view: Callable
        if self.is_async:
            view = self._async_view
        else:
            view = self._sync_view

        view.__func__.csrf_exempt = True  # type: ignore
        return view

    def _sync_view(self, request: HttpRequest, *a: Any, **kw: Any) -> HttpResponseBase:
        operation = self._find_operation(request)
        if operation is None:
            return self._not_allowed()
        return operation.run(request, *a, **kw)

    async def _async_view(
        self, request: HttpRequest, *a: Any, **kw: Any
    ) -> HttpResponseBase:
        from asgiref.sync import sync_to_async

        operation = self._find_operation(request)
        if operation is None:
            return self._not_allowed()
        if operation.is_async:
            return await cast(AsyncOperation, operation).run(request, *a, **kw)
        return await sync_to_async(operation.run)(request, *a, **kw)

    def _find_operation(self, request: HttpRequest) -> Optional[Operation]:
        for op in self.operations:
            if request.method in op.methods:
                return op
        return None

    def _not_allowed(self) -> HttpResponse:
        allowed_methods = set()
        for op in self.operations:
            allowed_methods.update(op.methods)
        return HttpResponseNotAllowed(allowed_methods, content=b"Method not allowed")


class ResponseObject:
    "Basically this is just a helper to be able to pass response to pydantic's model_validate"

    def __init__(self, response: HttpResponse) -> None:
        self.response = response
