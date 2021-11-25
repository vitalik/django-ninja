import inspect
from abc import ABC, abstractmethod
from functools import wraps
from typing import Any, Callable, Optional, Tuple, Type

from django.db.models import QuerySet
from django.utils.module_loading import import_string

from ninja import Field, Query, Schema
from ninja.conf import settings
from ninja.constants import NOT_SET
from ninja.types import DictStrAny


class PaginationBase(ABC):
    name_param: str = "pagination"
    pass_parameter: Optional[str] = None

    class Input(Schema):
        pass

    InputSource = Query(...)

    def __init__(self, pass_parameter: Optional[str] = None, **kwargs: Any) -> None:
        self.pass_parameter = pass_parameter or self.pass_parameter

    @abstractmethod
    def paginate_queryset(self, items: QuerySet, **params: DictStrAny) -> QuerySet:
        pass  # pragma: no cover


class LimitOffsetPagination(PaginationBase):
    class Input(Schema):
        limit: int = Field(settings.PAGINATION_PER_PAGE, gt=0)
        offset: int = Field(0, gt=-1)

    def paginate_queryset(self, items: QuerySet, **params: DictStrAny) -> QuerySet:
        offset: int
        limit: int
        limit, offset = params[self.name_param].limit, params[self.name_param].offset  # type: ignore

        return items[offset : offset + limit]  # noqa: E203


class PageNumberPagination(PaginationBase):
    class Input(Schema):
        page: int = Field(1, gt=0)

    def __init__(
        self, page_size: int = settings.PAGINATION_PER_PAGE, **kwargs: Any
    ) -> None:
        self.page_size = page_size
        super().__init__(**kwargs)

    def paginate_queryset(self, items: QuerySet, **params: DictStrAny) -> QuerySet:
        page: int = params[self.name_param].page  # type: ignore
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
    **paginator_params: Any,
) -> Callable:
    paginator: PaginationBase = paginator_class(**paginator_params)

    @wraps(func)
    def view_with_pagination(*args: Tuple[Any], **kwargs: DictStrAny) -> Any:
        paginate_param = kwargs.pop(paginator.name_param)
        if paginator.pass_parameter:
            kwargs[paginator.pass_parameter] = paginate_param
        items = func(*args, **kwargs)
        return paginator.paginate_queryset(
            items,
            **{paginator.name_param: paginate_param, **kwargs},
        )

    view_with_pagination._ninja_contribute_args = [  # type: ignore
        (
            paginator.name_param,
            paginator.Input,
            paginator.InputSource,
        ),
    ]

    return view_with_pagination
