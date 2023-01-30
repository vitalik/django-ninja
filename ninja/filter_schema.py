from typing import TYPE_CHECKING, ClassVar, Type

from django.core.exceptions import ImproperlyConfigured
from django.db.models import Q, QuerySet
from pydantic import BaseConfig
from typing_extensions import Literal

from .schema import Schema


class FilterConfig(BaseConfig):
    ignore_none: bool = True
    expression_connector: Literal["AND", "OR", "XOR"] = "AND"


class FilterSchema(Schema):
    """
    A Schema subclass that can be used for filtering in API handlers.

    === Declaration ===
    Inherit from this class and list the fields you want to filter by.
    On the right-hand side of the definition define a lookup that will be used for filtering using 'q' kwarg:

    class BookFilterSchema(FilterSchema):
        name: Optional[str] = Field(q='name__icontains')
        author: Optional[str] = Field(q='author__name__icontains')
        created_after: Optional[datetime] = Field(q='created__gte')


    === Usage in API ===

    Use .filter method to filter your queryset based on the filters set:

    @api.get("/books")
    def list_books(request, filters: BookFilterSchema = Query(...)):
        books = Book.objects.all()
        books = filters.filter(books)
        return books


    Alternatively, you can get the filter expression and perform the filtering yourself.
    That can be useful, when you have some additional query filtering on top of what you expose to the API:

    @api.get("/books")
    def list_books(request, filters: BookFilterSchema = Query(...)):
        q = (Q(author__is_active=True) | Q(publisher__is_active=True))
        q &= filters.get_filter_expression()
        return Book.objects.filter(q)


    === Customizability ===

    1. By default, None values are not filtered by.
            You can change that using 'Field(ignore_none=False)' on a field level
            or using 'Config.ignore_none = False' or a class level

        class BookFilterSchema(FilterSchema):
            name: Optional[str] = Field(q='name__icontains', ignore_none=False)
            created_after: Optional[datetime] = Field(q='created__gte')

    2. By default, field expressions are combined using 'AND'.
       You can change that using 'Config.expression_connector = "OR"'

        class BookFilterSchema(FilterSchema):
            name: Optional[str] = Field(q='name__icontains')
            created_after: Optional[datetime] = Field(q='created__gte')

            class Config:
                expression_connector = 'OR'

    3. Instead of defining Q expressions per each field, you can provide a 'custom_expression' method:

    class BookFilterSchema(FilterSchema):
            name: Optional[str]

            def custom_expression(self):
                q = Q()
                if self.name:
                    q &= (Q(name__icontains=self.name) | Q(author__name__icontains=self.name))
                return q


    """

    if TYPE_CHECKING:
        __config__: ClassVar[Type[FilterConfig]] = FilterConfig  # pragma: no cover

    Config = FilterConfig

    def custom_expression(self) -> Q:
        """
        Implement this method to return a combination of filters that will be used
        """
        raise NotImplementedError

    def get_filter_expression(self) -> Q:
        """
        Returns a Q expression based on the current filters
        """
        try:
            return self.custom_expression()
        except NotImplementedError:
            return self._connect_fields()

    def filter(self, queryset: QuerySet) -> QuerySet:
        return queryset.filter(self.get_filter_expression())

    def _connect_fields(self) -> Q:

        q = Q()
        for field_name, field in self.__fields__.items():
            filter_value = getattr(self, field_name)
            q_expression = field.field_info.extra.get("q", None)
            ignore_none = field.field_info.extra.get(
                "ignore_none", self.__config__.ignore_none
            )
            if not q_expression:
                raise ImproperlyConfigured(
                    f"Field {field_name} of {self.__class__.__name__} has not defined a Q expression.\n"
                    f"Define a Q expression the field definition under 'q' kwarg:\n"
                    f"  {field_name}: {field.annotation} = Field(..., q='<here>')\n"
                    f"Alternatively, you can implement {self.__class__.__name__}.custom_expression that must return a Q expression"
                )
            if filter_value is None and ignore_none:
                continue

            # _combine is a private method of Q
            # Qs could be combined with &, | and ^, but that would require an ugly switch-case
            q = q._combine(  # type: ignore[attr-defined]
                Q(**{q_expression: filter_value}), self.__config__.expression_connector
            )
        return q
