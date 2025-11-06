import binascii
import inspect
from abc import ABC, abstractmethod
from base64 import b64decode, b64encode
from functools import partial, wraps
from math import inf
from typing import (
    Annotated,
    Any,
    AsyncGenerator,
    Callable,
    List,
    Optional,
    Tuple,
    Type,
    Union,
)
from urllib import parse

from django.db.models import QuerySet
from django.http import HttpRequest
from django.utils.module_loading import import_string
from pydantic import BaseModel, field_validator
from typing_extensions import get_args as get_collection_args

from ninja import Field, Query, Router, Schema
from ninja.conf import settings
from ninja.constants import NOT_SET
from ninja.errors import ConfigError, ValidationError
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
        request: HttpRequest,
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
        request: HttpRequest,
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
            le=(
                settings.PAGINATION_MAX_LIMIT
                if settings.PAGINATION_MAX_LIMIT != inf
                else None
            ),
        )
        offset: int = Field(0, ge=0)

    def paginate_queryset(
        self,
        queryset: QuerySet,
        pagination: Input,
        request: HttpRequest,
        **params: Any,
    ) -> Any:
        offset = pagination.offset
        limit: int = min(pagination.limit, settings.PAGINATION_MAX_LIMIT)
        return {
            self.items_attribute: queryset[offset : offset + limit],
            "count": self._items_count(queryset),
        }  # noqa: E203

    async def apaginate_queryset(
        self,
        queryset: QuerySet,
        pagination: Input,
        request: HttpRequest,
        **params: Any,
    ) -> Any:
        offset = pagination.offset
        limit: int = min(pagination.limit, settings.PAGINATION_MAX_LIMIT)
        if isinstance(queryset, QuerySet):
            items = [obj async for obj in queryset[offset : offset + limit]]
        else:
            items = queryset[offset : offset + limit]
        return {
            self.items_attribute: items,
            "count": await self._aitems_count(queryset),
        }  # noqa: E203


class PageNumberPagination(AsyncPaginationBase):
    class Input(Schema):
        page: int = Field(1, ge=1)
        page_size: Optional[int] = Field(None, ge=1)

    def __init__(
        self,
        page_size: int = settings.PAGINATION_PER_PAGE,
        max_page_size: int = settings.PAGINATION_MAX_PER_PAGE_SIZE,
        **kwargs: Any,
    ) -> None:
        self.page_size = page_size
        self.max_page_size = max_page_size
        super().__init__(**kwargs)

    def _get_page_size(self, requested_page_size: Optional[int]) -> int:
        if requested_page_size is None:
            return self.page_size

        return min(requested_page_size, self.max_page_size)

    def paginate_queryset(
        self,
        queryset: QuerySet,
        pagination: Input,
        request: HttpRequest,
        **params: Any,
    ) -> Any:
        page_size = self._get_page_size(pagination.page_size)
        offset = (pagination.page - 1) * page_size
        return {
            self.items_attribute: queryset[offset : offset + page_size],
            "count": self._items_count(queryset),
        }  # noqa: E203

    async def apaginate_queryset(
        self,
        queryset: QuerySet,
        pagination: Input,
        request: HttpRequest,
        **params: Any,
    ) -> Any:
        page_size = self._get_page_size(pagination.page_size)
        offset = (pagination.page - 1) * page_size

        if isinstance(queryset, QuerySet):
            items = [obj async for obj in queryset[offset : offset + page_size]]
        else:
            items = queryset[offset : offset + page_size]

        return {
            self.items_attribute: items,
            "count": await self._aitems_count(queryset),
        }  # noqa: E203


class CursorPagination(AsyncPaginationBase):
    max_page_size: int
    page_size: int

    items_attribute: str = "results"

    def __init__(
        self,
        *,
        ordering: tuple[str, ...] = settings.PAGINATION_DEFAULT_ORDERING,
        page_size: int = settings.PAGINATION_PER_PAGE,
        max_page_size: int = settings.PAGINATION_MAX_PER_PAGE_SIZE,
        **kwargs: Any,
    ) -> None:
        self.ordering = ordering
        # take the first ordering parameter as the attribute for establishing
        # position
        self._order_attribute = (
            ordering[0][1:] if ordering[0].startswith("-") else ordering[0]
        )
        self._order_attribute_reversed = ordering[0].startswith("-")

        self.page_size = page_size
        self.max_page_size = max_page_size

        super().__init__(**kwargs)

    class Input(Schema):
        page_size: int | None = None
        cursor: str | None = None

    class Output(Schema):
        previous: str | None
        next: str | None
        results: list[Any]

    class Cursor(BaseModel):
        """
        Represents pagination state.

        This is encoded in a base64 query parameter.

        """

        p: Annotated[
            str | None,
            Field(
                title="position",
                description="String identifier for the current position in the dataset",
            ),
        ] = None
        r: Annotated[
            bool,
            Field(
                title="reverse", description="Whether to reverse the ordering direction"
            ),
        ] = False
        # offset enables the use of a non-unique ordering field
        # e.g. if created time of two items is exactly the same, we can use the offset
        # to figure out the position exactly
        o: Annotated[
            int,
            Field(
                ge=0,
                lt=settings.PAGINATION_MAX_OFFSET,
                title="offset",
                description="Number of items to skip from the current position",
            ),
        ] = 0

        @field_validator("*", mode="before")
        @classmethod
        def validate_individual_queryparam(cls, value: Any) -> Any:
            """
            Handle query string parsing quirks where single values become lists.

            URL parsing libraries wrap single query parameters in lists, we only
            care about a single value
            """
            if isinstance(value, list):
                return value[0]
            return value

        @classmethod
        def from_encoded_param(
            cls, encoded_param: str | None, context: Any = None
        ) -> "CursorPagination.Cursor":
            """
            Deserialize cursor from URL-safe base64 token.
            """
            if not encoded_param:
                return cls()
            try:
                decoded = b64decode(
                    encoded_param.encode("ascii"), validate=True
                ).decode("ascii")
            except (ValueError, binascii.Error) as e:
                raise ValidationError([{"cursor": "Invalid Cursor"}]) from e

            parsed_querystring = parse.parse_qs(decoded, keep_blank_values=True)
            return cls.model_validate(parsed_querystring, context=context)

        def encode_as_param(self) -> str:
            """
            Serialize cursor to URL-safe base64 token.
            """
            data = self.model_dump(
                exclude_defaults=True, exclude_none=True, exclude_unset=True
            )
            query_string = parse.urlencode(data, doseq=True)
            return b64encode(query_string.encode("ascii")).decode("ascii")

    @staticmethod
    def _reverse_order(order: tuple[str, ...]) -> tuple[str, ...]:
        """
        Flip ordering direction for backward pagination.

        Example:
            ("-created", "pk") becomes ("created", "-pk")
            ("name", "-updated") becomes ("-name", "updated")
        """
        return tuple(
            marker[1:] if marker.startswith("-") else f"-{marker}" for marker in order
        )

    def _get_position(self, item: Any) -> str:
        """
        Extract the string representation of the attribute value used for ordering,
        which serves as the position identifier.

        """
        return str(getattr(item, self._order_attribute))

    def _get_page_size(self, requested_page_size: int | None) -> int:
        """
        Determine the actual page size to use, respecting configured limits.

        Uses the default page size when no specific size is requested, otherwise
        clamps the requested size within the allowed range to prevent resource
        exhaustion attacks.
        """
        if requested_page_size is None:
            return self.page_size
        return min(self.max_page_size, max(1, requested_page_size))

    def _build_next_cursor(
        self,
        current_cursor: Cursor,
        results: list[Any],
        additional_position: str | None = None,
    ) -> Cursor | None:
        """
        Build cursor for next page
        """
        if (additional_position is None and not current_cursor.r) or not results:
            return None

        if not current_cursor.r:
            # next position is provided by the additional position in a forward cursor
            next_position = additional_position
        else:
            # default to the last item
            # this will result in this item being included in the next set of results
            # when flipping from a reversed cursor query to a forward cursor query
            next_position = self._get_position(results[-1])

        offset = 0

        if current_cursor.p == next_position and not current_cursor.r:
            offset += current_cursor.o + len(results)
        else:
            # Count duplicates at page end to find the offset
            for item in reversed(results):
                item_position_value = self._get_position(item)
                if item_position_value != next_position:
                    break
                offset += 1

        return self.Cursor(o=offset, r=False, p=next_position)

    def _build_previous_cursor(
        self,
        current_cursor: Cursor,
        results: list[Any],
        additional_position: str | None = None,
    ) -> Cursor | None:
        """
        Build cursor for previous page
        """
        if (
            current_cursor.r and additional_position is None
        ) or current_cursor.p is None:
            return None

        if not results:
            # End of dataset - create reverse cursor to go backward
            return self.Cursor(o=0, r=True, p=current_cursor.p)

        if current_cursor.r:
            # previous position is provided by the additional position in a
            # reversed cursor
            previous_position = additional_position

        else:
            # default to the first item
            # this will result in this item being included in the previous set of
            # results when flipping from a forward cursor query to a reversed
            # cursor query
            previous_position = self._get_position(results[0])

        offset = 0

        if current_cursor.p == previous_position and current_cursor.r:
            offset += current_cursor.o + len(results)
        else:
            # Count duplicates at page end to find the offset
            for item in results:
                item_position_value = self._get_position(item)
                if item_position_value != previous_position:
                    break
                offset += 1

        return self.Cursor(o=offset, r=True, p=previous_position)

    @staticmethod
    def _add_cursor_to_URL(url: str, cursor: Cursor | None) -> str | None:
        """
        Build pagination URLs with an encoded cursor.

        Ignore any previous cursors but preserve any other query parameters

        Example:
            Given URL "https://api.example.com/pages?tag=hiring" and a cursor
            with position "2024-01-01T10:00:00Z", returns:
            "https://api.example.com/pages?cursor=cD0yMDI0LTAxLTAxVDEwJTNBMDA%3D&tag=hiring"
        """

        if cursor is None:
            return None
        (scheme, netloc, path, query, fragment) = parse.urlsplit(url)
        query_dict = parse.parse_qs(query, keep_blank_values=True)
        query_dict["cursor"] = [cursor.encode_as_param()]
        query = parse.urlencode(sorted(query_dict.items()), doseq=True)
        return parse.urlunsplit((scheme, netloc, path, query, fragment))

    def _order_queryset(self, queryset: QuerySet, cursor: Cursor) -> QuerySet:
        """
        Apply ordering to queryset based on cursor direction.

        For backward pagination (cursor.r=True), flips the ordering direction
        to traverse the dataset in reverse.
        """
        if cursor.r:
            return queryset.order_by(*self._reverse_order(self.ordering))

        return queryset.order_by(*self.ordering)

    def _find_position(self, queryset: QuerySet, cursor: Cursor) -> QuerySet:
        """
        Filter queryset to start from the cursor position.
        """
        if cursor.p is None:
            return queryset

        cmp = "gte" if cursor.r == self._order_attribute_reversed else "lte"
        filters = {f"{self._order_attribute}__{cmp}": cursor.p}
        return queryset.filter(**filters)

    def paginate_queryset(
        self, queryset: QuerySet, pagination: Input, request: HttpRequest, **params: Any
    ) -> Any:
        """
        Execute cursor-based pagination with stable positioning.

        We fetch page_size + 1 items to detect whether more pages exist without
        requiring a separate count query. The extra item is discarded from results
        but used for next/previous cursor generation.
        """
        page_size = self._get_page_size(pagination.page_size)
        cursor = self.Cursor.from_encoded_param(pagination.cursor)

        queryset = self._order_queryset(queryset, cursor)
        queryset = self._find_position(queryset, cursor)

        # fetch results here and turn into a list
        results_plus_one = list(queryset[cursor.o : cursor.o + page_size + 1])
        additional_position = (
            self._get_position(results_plus_one[-1])
            if len(results_plus_one) > page_size
            else None
        )

        if cursor.r:
            results = list(reversed(results_plus_one[:page_size]))
        else:
            results = results_plus_one[:page_size]

        next_cursor = self._build_next_cursor(
            current_cursor=cursor,
            results=results,
            additional_position=additional_position,
        )

        previous_cursor = self._build_previous_cursor(
            current_cursor=cursor,
            results=results,
            additional_position=additional_position,
        )

        base_url = request.build_absolute_uri()

        return {
            "next": self._add_cursor_to_URL(base_url, next_cursor),
            "previous": self._add_cursor_to_URL(base_url, previous_cursor),
            self.items_attribute: results,
        }

    async def apaginate_queryset(
        self,
        queryset: QuerySet,
        pagination: Input,
        request: HttpRequest,
        **params: Any,
    ) -> Any:
        """
        Execute async cursor-based pagination with stable positioning.

        We fetch page_size + 1 items to detect whether more pages exist without
        requiring a separate count query. The extra item is discarded from results
        but used for next/previous cursor generation.
        """
        page_size = self._get_page_size(pagination.page_size)
        cursor = self.Cursor.from_encoded_param(pagination.cursor)

        queryset = self._order_queryset(queryset, cursor)
        queryset = self._find_position(queryset, cursor)

        # fetch results here and turn into a list
        results_plus_one = [
            obj async for obj in queryset[cursor.o : cursor.o + page_size + 1]
        ]
        additional_position = (
            self._get_position(results_plus_one[-1])
            if len(results_plus_one) > page_size
            else None
        )

        if cursor.r:
            results = list(reversed(results_plus_one[:page_size]))
        else:
            results = results_plus_one[:page_size]

        next_cursor = self._build_next_cursor(
            current_cursor=cursor,
            results=results,
            additional_position=additional_position,
        )

        previous_cursor = self._build_previous_cursor(
            current_cursor=cursor,
            results=results,
            additional_position=additional_position,
        )

        base_url = request.build_absolute_uri()

        return {
            "next": self._add_cursor_to_URL(base_url, next_cursor),
            "previous": self._add_cursor_to_URL(base_url, previous_cursor),
            self.items_attribute: results,
        }


def paginate(
    func_or_pgn_class: Any = NOT_SET, **paginator_params: Any
) -> Callable[..., Any]:
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

    def wrapper(func: Callable[..., Any]) -> Any:
        return _inject_pagination(func, pagination_class, **paginator_params)

    return wrapper


def _inject_pagination(
    func: Callable[..., Any],
    paginator_class: Type[Union[PaginationBase, AsyncPaginationBase]],
    **paginator_params: Any,
) -> Callable[..., Any]:
    if getattr(func, "_ninja_is_paginated", False):
        return func  # ^ user changed pagination manually on function already

    paginator = paginator_class(**paginator_params)

    # Check if Input schema has any fields
    # If it has no fields, we should make it optional to support Pydantic 2.12+
    has_input_fields = bool(paginator.Input.model_fields)

    if is_async_callable(func):
        if not hasattr(paginator, "apaginate_queryset"):
            raise ConfigError("Pagination class not configured for async requests")

        @wraps(func)
        async def view_with_pagination(request: HttpRequest, **kwargs: Any) -> Any:
            pagination_params = kwargs.pop("ninja_pagination", None)
            if pagination_params is None:
                pagination_params = paginator.Input()
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
            pagination_params = kwargs.pop("ninja_pagination", None)
            if pagination_params is None:
                pagination_params = paginator.Input()
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

    # Only contribute args if Input has fields
    # For empty Input schemas, don't add the parameter at all to support Pydantic 2.12+
    if has_input_fields:
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

    view_with_pagination._ninja_is_paginated = True  # type: ignore
    return view_with_pagination


class RouterPaginated(Router):
    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        self.pagination_class = import_string(settings.PAGINATION_CLASS)

    def add_api_operation(
        self,
        path: str,
        methods: List[str],
        view_func: Callable[..., Any],
        **kwargs: Any,
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
    except AttributeError:  # pragma: no cover
        # special case for `typing.Any`, only raised for Python < 3.10
        new_name = f"Paged{str(item_schema).replace('.', '_')}"  # pragma: no cover
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
