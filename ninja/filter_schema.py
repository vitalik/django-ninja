from typing import TYPE_CHECKING, Any, ClassVar, Type, cast

from django.core.exceptions import ImproperlyConfigured
from django.db.models import Q, QuerySet
from pydantic import BaseConfig
from pydantic.fields import ModelField
from typing_extensions import Literal

from .schema import Schema

DEFAULT_IGNORE_NONE = True
DEFAULT_CLASS_LEVEL_EXPRESSION_CONNECTOR = "AND"
DEFAULT_FIELD_LEVEL_EXPRESSION_CONNECTOR = "OR"

# XOR is available only in Django 4.1+: https://docs.djangoproject.com/en/4.1/ref/models/querysets/#xor
ExpressionConnector = Literal["AND", "OR", "XOR"]


class FilterConfig(BaseConfig):
    ignore_none: bool = DEFAULT_IGNORE_NONE
    expression_connector: ExpressionConnector = cast(
        ExpressionConnector, DEFAULT_CLASS_LEVEL_EXPRESSION_CONNECTOR
    )


class FilterSchema(Schema):
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

    def _resolve_field_expression(
        self, field_name: str, field_value: Any, field: ModelField
    ) -> Q:
        func = getattr(self, f"filter_{field_name}", None)
        if callable(func):
            return func(field_value)  # type: ignore[no-any-return]

        q_expression = field.field_info.extra.get("q", None)
        if not q_expression:
            return Q(**{field_name: field_value})
        elif isinstance(q_expression, str):
            return Q(**{q_expression: field_value})
        elif isinstance(q_expression, list):
            expression_connector = field.field_info.extra.get(
                "expression_connector", DEFAULT_FIELD_LEVEL_EXPRESSION_CONNECTOR
            )
            q = Q()
            for q_expression_part in q_expression:
                q = q._combine(Q(**{q_expression_part: field_value}), expression_connector)  # type: ignore[attr-defined]
            return q
        else:
            raise ImproperlyConfigured(
                f"Field {field_name} of {self.__class__.__name__} defines an invalid value under 'q' kwarg.\n"
                f"Define a 'q' kwarg as a string or a list of strings, each string corresponding to a database lookup you wish to filter against:\n"
                f"  {field_name}: {field.annotation} = Field(..., q='<here>')\n"
                f"or\n"
                f"  {field_name}: {field.annotation} = Field(..., q=['lookup1', 'lookup2', ...])\n"
                f"Alternatively, you can implement {self.__class__.__name__}.filter_{field_name} that must return a Q expression for that field"
            )

    def _connect_fields(self) -> Q:
        q = Q()
        for field_name, field in self.__fields__.items():
            filter_value = getattr(self, field_name)
            ignore_none = field.field_info.extra.get(
                "ignore_none", self.__config__.ignore_none
            )

            # Resolve q for a field even if we skip it due to None value
            # So that improperly configured fields are easier to detect
            field_q = self._resolve_field_expression(field_name, filter_value, field)
            if filter_value is None and ignore_none:
                continue
            q = q._combine(field_q, self.__config__.expression_connector)  # type: ignore[attr-defined]

        return q
