import inspect
from abc import ABC, abstractmethod
from functools import partial, wraps
from typing import Any, Callable, List, Optional, Tuple, Type

from django.db.models import QuerySet
from django.utils.module_loading import import_string

from ninja import Field, Query, Router, Schema
from ninja.compatibility.util import get_args as get_collection_args
from ninja.conf import settings
from ninja.constants import NOT_SET
from ninja.errors import ConfigError
from ninja.operation import Operation
from ninja.signature.details import is_collection_type
from ninja.types import DictStrAny


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
        **params: DictStrAny,
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


class LimitOffsetPagination(PaginationBase):
    class Input(Schema):
        limit: int = Field(settings.PAGINATION_PER_PAGE, ge=1)
        offset: int = Field(0, ge=0)

    def paginate_queryset(
        self,
        queryset: QuerySet,
        pagination: Input,
        **params: DictStrAny,
    ) -> Any:
        offset = pagination.offset
        limit: int = pagination.limit
        return {
            "items": queryset[offset : offset + limit],
            "count": self._items_count(queryset),
        }  # noqa: E203


class PageNumberPagination(PaginationBase):
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
        **params: DictStrAny,
    ) -> Any:
        offset = (pagination.page - 1) * self.page_size
        return {
            "items": queryset[offset : offset + self.page_size],
            "count": self._items_count(queryset),
        }  # noqa: E203


def paginate(
    func_or_pgn_class: Any = NOT_SET, **paginator_params: DictStrAny
) -> Callable:
    """
    @api.get(...
    @paginage
    def my_view(request):

    or

    @api.get(...
    @paginage(PageNumberPagination)
    def my_view(request):

    """

    isfunction = inspect.isfunction(func_or_pgn_class)
    isnotset = func_or_pgn_class == NOT_SET

    pagination_class: Type[PaginationBase] = import_string(settings.PAGINATION_CLASS)

    if isfunction:
        return _inject_pagination(func_or_pgn_class, pagination_class)

    if not isnotset:
        pagination_class = func_or_pgn_class

    def wrapper(func: Callable) -> Any:
        return _inject_pagination(func, pagination_class, **paginator_params)

    return wrapper


def _inject_pagination(
    func: Callable,
    paginator_class: Type[PaginationBase],
    **paginator_params: Any,
) -> Callable:
    paginator: PaginationBase = paginator_class(**paginator_params)

    @wraps(func)
    def view_with_pagination(*args: Tuple[Any], **kwargs: DictStrAny) -> Any:
        pagination_params = kwargs.pop("ninja_pagination")
        if paginator.pass_parameter:
            kwargs[paginator.pass_parameter] = pagination_params

        items = func(*args, **kwargs)

        result = paginator.paginate_queryset(
            items, pagination=pagination_params, **kwargs
        )
        if paginator.Output:
            result[paginator.items_attribute] = list(result[paginator.items_attribute])
            # ^ forcing queryset evaluation #TODO: check why pydantic did not do it here
        return result

    view_with_pagination._ninja_contribute_args = [  # type: ignore
        (
            "ninja_pagination",
            paginator.Input,
            paginator.InputSource,
        ),
    ]

    # def contribute_to_operation(op: Operation) -> None:

    #     make_response_paginated(schema, paginator, op)

    if paginator.Output:
        view_with_pagination._ninja_contribute_to_operation = partial(  # type: ignore
            make_response_paginated, paginator
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
    where Paged some willbe a subclass of paginator.Output:
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
            paginator.items_attribute: [],
        },
    )  # typing: ignore

    response = op._create_response_model(new_schema)

    # Changing response model to newly created one
    op.response_models[status_code] = response


def _find_collection_response(op: Operation) -> Tuple[int, Any]:
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
