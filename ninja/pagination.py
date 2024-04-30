import inspect
from abc import ABC, abstractmethod
from functools import partial, wraps
from math import inf
from typing import Any, AsyncGenerator, Callable, List, Optional, Tuple, Type, Union

from django.db.models import QuerySet
from django.http import HttpRequest
from django.utils.module_loading import import_string
from typing_extensions import get_args as get_collection_args

from ninja import Field, Query, Router, Schema
from ninja.conf import settings
from ninja.constants import NOT_SET
from ninja.errors import ConfigError
from ninja.operation import Operation
from ninja.signature.details import is_collection_type
from ninja.utils import (
    contribute_operation_args,
    contribute_operation_callback,
    is_async_callable,
)


class PaginationBase(ABC):
    class Input(Schema):
        pass

    InputSource = Query(...)

    class Output(Schema):
        items: List[Any]
        count: int

    items_attribute: str = "items"

    def __init__(self, *, pass_parameter: Optional[str] = None, **kwargs: Any) -> None:
        self.pass_parameter = pass_parameter

    @abstractmethod
    def paginate_queryset(
        self,
        queryset: QuerySet,
        pagination: Any,
        **params: Any,
    ) -> Any:
        pass  # pragma: no cover

    def _items_count(self, queryset: QuerySet) -> int:
        """
        Since lists are mainly compatible with QuerySets and can be passed to paginator.
        We will first to try to use .count - and if not there will use a len
        """
        try:
            # forcing to find queryset.count instead of list.count:
            return queryset.all().count()
        except AttributeError:
            return len(queryset)


class AsyncPaginationBase(PaginationBase):
    @abstractmethod
    async def apaginate_queryset(
        self,
        queryset: QuerySet,
        pagination: Any,
        **params: Any,
    ) -> Any:
        pass  # pragma: no cover

    async def _aitems_count(self, queryset: QuerySet) -> int:
        try:
            return await queryset.all().acount()
        except AttributeError:
            return len(queryset)


class LimitOffsetPagination(AsyncPaginationBase):
    class Input(Schema):
        limit: int = Field(
            settings.PAGINATION_PER_PAGE,
            ge=1,
            le=settings.PAGINATION_MAX_LIMIT
            if settings.PAGINATION_MAX_LIMIT != inf
            else None,
        )
        offset: int = Field(0, ge=0)

    def paginate_queryset(
        self,
        queryset: QuerySet,
        pagination: Input,
        **params: Any,
    ) -> Any:
        offset = pagination.offset
        limit: int = min(pagination.limit, settings.PAGINATION_MAX_LIMIT)
        return {
            "items": queryset[offset : offset + limit],
            "count": self._items_count(queryset),
        }  # noqa: E203

    async def apaginate_queryset(
        self,
        queryset: QuerySet,
        pagination: Input,
        **params: Any,
    ) -> Any:
        offset = pagination.offset
        limit: int = min(pagination.limit, settings.PAGINATION_MAX_LIMIT)
        return {
            "items": queryset[offset : offset + limit],
            "count": await self._aitems_count(queryset),
        }  # noqa: E203


class PageNumberPagination(AsyncPaginationBase):
    class Input(Schema):
        page: int = Field(1, ge=1)

    def __init__(
        self, page_size: int = settings.PAGINATION_PER_PAGE, **kwargs: Any
    ) -> None:
        self.page_size = page_size
        super().__init__(**kwargs)

    def paginate_queryset(
        self,
        queryset: QuerySet,
        pagination: Input,
        **params: Any,
    ) -> Any:
        offset = (pagination.page - 1) * self.page_size
        return {
            "items": queryset[offset : offset + self.page_size],
            "count": self._items_count(queryset),
        }  # noqa: E203

    async def apaginate_queryset(
        self,
        queryset: QuerySet,
        pagination: Input,
        **params: Any,
    ) -> Any:
        offset = (pagination.page - 1) * self.page_size
        return {
            "items": queryset[offset : offset + self.page_size],
            "count": await self._aitems_count(queryset),
        }  # noqa: E203


def paginate(func_or_pgn_class: Any = NOT_SET, **paginator_params: Any) -> Callable:
    """
    @api.get(...
    @paginate
    def my_view(request):

    or

    @api.get(...
    @paginate(PageNumberPagination)
    def my_view(request):

    """

    isfunction = inspect.isfunction(func_or_pgn_class)
    isnotset = func_or_pgn_class == NOT_SET

    pagination_class: Type[Union[PaginationBase, AsyncPaginationBase]] = import_string(
        settings.PAGINATION_CLASS
    )

    if isfunction:
        return _inject_pagination(func_or_pgn_class, pagination_class)

    if not isnotset:
        pagination_class = func_or_pgn_class

    def wrapper(func: Callable) -> Any:
        return _inject_pagination(func, pagination_class, **paginator_params)

    return wrapper


def _inject_pagination(
    func: Callable,
    paginator_class: Type[Union[PaginationBase, AsyncPaginationBase]],
    **paginator_params: Any,
) -> Callable:
    paginator = paginator_class(**paginator_params)
    if is_async_callable(func):
        if not hasattr(paginator, "apaginate_queryset"):
            raise ConfigError("Pagination class not configured for async requests")

        @wraps(func)
        async def view_with_pagination(request: HttpRequest, **kwargs: Any) -> Any:
            pagination_params = kwargs.pop("ninja_pagination")
            if paginator.pass_parameter:
                kwargs[paginator.pass_parameter] = pagination_params

            items = await func(request, **kwargs)

            result = await paginator.apaginate_queryset(
                items, pagination=pagination_params, request=request, **kwargs
            )

            async def evaluate(results: Union[List, QuerySet]) -> AsyncGenerator:
                for result in results:
                    yield result

            if paginator.Output:  # type: ignore
                result[paginator.items_attribute] = [
                    result
                    async for result in evaluate(result[paginator.items_attribute])
                ]
            return result

    else:

        @wraps(func)
        def view_with_pagination(request: HttpRequest, **kwargs: Any) -> Any:
            pagination_params = kwargs.pop("ninja_pagination")
            if paginator.pass_parameter:
                kwargs[paginator.pass_parameter] = pagination_params

            items = func(request, **kwargs)

            result = paginator.paginate_queryset(
                items, pagination=pagination_params, request=request, **kwargs
            )
            if paginator.Output:  # type: ignore
                result[paginator.items_attribute] = list(
                    result[paginator.items_attribute]
                )
                # ^ forcing queryset evaluation #TODO: check why pydantic did not do it here
            return result

    contribute_operation_args(
        view_with_pagination,
        "ninja_pagination",
        paginator.Input,
        paginator.InputSource,
    )

    if paginator.Output:  # type: ignore
        contribute_operation_callback(
            view_with_pagination,
            partial(make_response_paginated, paginator),
        )

    return view_with_pagination


class RouterPaginated(Router):
    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        self.pagination_class = import_string(settings.PAGINATION_CLASS)

    def add_api_operation(
        self, path: str, methods: List[str], view_func: Callable, **kwargs: Any
    ) -> None:
        response = kwargs["response"]
        if is_collection_type(response):
            view_func = _inject_pagination(view_func, self.pagination_class)
        return super().add_api_operation(path, methods, view_func, **kwargs)


def make_response_paginated(paginator: PaginationBase, op: Operation) -> None:
    """
    Takes operation response and changes it to the paginated response
    for example:
        response=List[Some]
    will be changed to:
        response=PagedSome
    where Paged some will be a subclass of paginator.Output:
        class PagedSome:
            items: List[Some]
            count: int
    """
    status_code, item_schema = _find_collection_response(op)

    # Switching schema to Output schema
    try:
        new_name = f"Paged{item_schema.__name__}"
    except AttributeError:
        new_name = f"Paged{str(item_schema).replace('.', '_')}"  # typing.Any case

    new_schema = type(
        new_name,
        (paginator.Output,),
        {
            "__annotations__": {paginator.items_attribute: List[item_schema]},  # type: ignore
        },
    )  # typing: ignore

    response = op._create_response_model(new_schema)

    # Changing response model to newly created one
    op.response_models[status_code] = response


def _find_collection_response(op: Operation) -> Tuple[int, Any]:
    """
    Walks through defined operation responses and finds the first
    that is of a collection type (e.g. List[SomeSchema])
    """
    for code, resp_model in op.response_models.items():
        if resp_model is None or resp_model is NOT_SET:
            continue

        model = resp_model.__annotations__["response"]
        if is_collection_type(model):
            item_schema = get_collection_args(model)[0]
            return code, item_schema

    raise ConfigError(
        f'"{op.view_func}" has no collection response (e.g. response=List[SomeSchema])'
    )
