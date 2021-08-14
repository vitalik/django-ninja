import inspect
from abc import ABC, abstractmethod
from functools import wraps
from typing import Any, Callable, Type

from django.db.models import QuerySet
from django.http import HttpRequest
from django.utils.module_loading import import_string

from ninja import Field, Query, Schema
from ninja.conf import settings
from ninja.constants import NOT_SET
from ninja.errors import ConfigError
from ninja.signature import has_kwargs
from ninja.types import DictStrAny


class PaginationBase(ABC):
    class Input(Schema):
        pass

    InputSource = Query(...)

    def __init__(self, **kwargs: DictStrAny) -> None:
        pass

    @abstractmethod
    def paginate_queryset(
        self, items: QuerySet, request: HttpRequest, **params: DictStrAny
    ) -> QuerySet:
        pass  # pragma: no cover


class LimitOffsetPagination(PaginationBase):
    class Input(Schema):
        limit: int = Field(settings.PAGINATION_PER_PAGE, gt=0)
        offset: int = Field(0, gt=-1)

    def paginate_queryset(
        self, items: QuerySet, request: HttpRequest, **params: DictStrAny
    ) -> QuerySet:
        offset: int
        limit: int
        limit, offset = params["pagination"].limit, params["pagination"].offset  # type: ignore

        return items[offset : offset + limit]  # noqa: E203


class PageNumberPagination(PaginationBase):
    class Input(Schema):
        page: int = Field(1, gt=0)

    def __init__(self, page_size: int = settings.PAGINATION_PER_PAGE) -> None:
        self.page_size = page_size

    def paginate_queryset(
        self, items: QuerySet, request: HttpRequest, **params: DictStrAny
    ) -> QuerySet:
        page: int = params["pagination"].page  # type: ignore
        offset = (page - 1) * self.page_size
        return items[offset : offset + self.page_size]  # noqa: E203


def paginate(
    func_or_pgn_class: Any = NOT_SET, **paginator_params: DictStrAny
) -> Callable:

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
    **paginator_params: DictStrAny,
) -> Callable:
    if not has_kwargs(func):
        raise ConfigError(
            f"function {func.__name__} must have **kwargs argument to be used with pagination"
        )

    paginator: PaginationBase = paginator_class(**paginator_params)

    @wraps(func)
    def view_with_pagination(request: HttpRequest, **kw: DictStrAny) -> Any:
        items = func(request, **kw)
        return paginator.paginate_queryset(items, request, **kw)

    view_with_pagination._ninja_contribute_args = [  # type: ignore
        (
            "pagination",
            paginator.Input,
            paginator.InputSource,
        ),
    ]

    return view_with_pagination
