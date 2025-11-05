import warnings
from typing import Any, List, Optional, TypeVar, Union, cast

from django.core.exceptions import ImproperlyConfigured
from django.db.models import Q, QuerySet
from pydantic import ConfigDict
from pydantic.fields import FieldInfo
from typing_extensions import Literal

from .constants import NOT_SET
from .schema import Schema

# XOR is available only in Django 4.1+: https://docs.djangoproject.com/en/4.1/ref/models/querysets/#xor
ExpressionConnector = Literal["AND", "OR", "XOR"]

DEFAULT_IGNORE_NONE: bool = True
DEFAULT_CLASS_LEVEL_EXPRESSION_CONNECTOR: ExpressionConnector = "AND"
DEFAULT_FIELD_LEVEL_EXPRESSION_CONNECTOR: ExpressionConnector = "OR"


class FilterLookup:
    """
    Annotation class for specifying database query lookups in FilterSchema fields.

    Example usage:
        class MyFilterSchema(FilterSchema):
            name: Annotated[Union[str, None], FilterLookup("name__icontains")] = None
            search: Annotated[Union[str, None], FilterLookup(["name__icontains", "email__icontains"])] = None
    """

    def __init__(
        self,
        q: Union[str, List[str], None],
        *,
        expression_connector: ExpressionConnector = DEFAULT_FIELD_LEVEL_EXPRESSION_CONNECTOR,
        ignore_none: bool = DEFAULT_IGNORE_NONE,
    ):
        """
        Args:
            q: Database lookup expression(s). Can be:
                - A string like "name__icontains"
                - A list of strings like ["name__icontains", "email__icontains"]
                - Use "__" prefix for implicit field name: "__icontains" becomes "fieldname__icontains"
            expression_connector: How to combine multiple field-level expressions ("OR", "AND", "XOR"). Default is "OR".
            ignore_none: Whether to ignore None values for this field specifically. Default is True.
        """
        self.q = q
        self.expression_connector = expression_connector
        self.ignore_none = ignore_none


T = TypeVar("T", bound=QuerySet)


class FilterConfigDict(ConfigDict, total=False):
    ignore_none: bool
    expression_connector: ExpressionConnector


class FilterSchema(Schema):
    model_config = FilterConfigDict(
        ignore_none=DEFAULT_IGNORE_NONE,
        expression_connector=DEFAULT_CLASS_LEVEL_EXPRESSION_CONNECTOR,
    )

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

    def filter(self, queryset: T) -> T:
        return queryset.filter(self.get_filter_expression())

    def _get_filter_lookup(
        self, field_name: str, field_info: FieldInfo
    ) -> Optional[FilterLookup]:
        if not hasattr(field_info, "metadata") or not field_info.metadata:
            return None

        filter_lookups = [
            metadata_item
            for metadata_item in field_info.metadata
            if isinstance(metadata_item, FilterLookup)
        ]

        if len(filter_lookups) == 0:
            return None
        elif len(filter_lookups) == 1:
            return filter_lookups[0]
        else:
            raise ImproperlyConfigured(
                f"Multiple FilterLookup instances found in metadata of {self.__class__.__name__}.{field_name}.\n"
                f"Use at most one FilterLookup instance per field.\n"
                f"If you need multiple lookups, specify them as a list in a single FilterLookup:\n"
                f"{field_name}: Annotated[{field_info.annotation}, FilterLookup(['lookup1', 'lookup2', ...])]"
            )

    def _get_field_q_expression(
        self,
        field_name: str,
        field_info: FieldInfo,
    ) -> Union[str, List[str], None]:
        filter_lookup = self._get_filter_lookup(field_name, field_info)
        if filter_lookup:
            return filter_lookup.q

        # Legacy approach, consider removing in future versions
        return cast(
            Union[str, List[str], None],
            self._get_from_deprecated_field_extra(field_name, field_info, "q"),
        )

    def _get_field_expression_connector(
        self,
        field_name: str,
        field_info: FieldInfo,
    ) -> Union[ExpressionConnector, None]:
        filter_lookup = self._get_filter_lookup(field_name, field_info)
        if filter_lookup:
            return filter_lookup.expression_connector

        # Legacy approach, consider removing in future versions
        return cast(
            Union[ExpressionConnector, None],
            self._get_from_deprecated_field_extra(
                field_name, field_info, "expression_connector"
            ),
        )

    def _get_field_ignore_none(
        self, field_name: str, field_info: FieldInfo
    ) -> Union[bool, None]:
        filter_lookup = self._get_filter_lookup(field_name, field_info)
        if filter_lookup:
            return filter_lookup.ignore_none

        # Legacy approach, consider removing in future versions
        return cast(
            Union[bool, None],
            self._get_from_deprecated_field_extra(
                field_name, field_info, "ignore_none"
            ),
        )

    def _resolve_field_expression(
        self, field_name: str, field_value: Any, field_info: FieldInfo
    ) -> Q:
        func = getattr(self, f"filter_{field_name}", None)
        if callable(func):
            return cast(Q, func(field_value))

        q_expression = self._get_field_q_expression(field_name, field_info)
        expression_connector = (
            self._get_field_expression_connector(field_name, field_info)
            or DEFAULT_FIELD_LEVEL_EXPRESSION_CONNECTOR
        )

        if not q_expression:
            return Q(**{field_name: field_value})
        elif isinstance(q_expression, str):
            if q_expression.startswith("__"):
                q_expression = f"{field_name}{q_expression}"
            return Q(**{q_expression: field_value})
        elif isinstance(q_expression, list) and all(
            isinstance(item, str) for item in q_expression
        ):
            q = Q()
            for q_expression_part in q_expression:
                if q_expression_part.startswith("__"):
                    q_expression_part = f"{field_name}{q_expression_part}"
                q = q._combine(  # type: ignore[attr-defined]
                    Q(**{q_expression_part: field_value}),
                    expression_connector,
                )
            return q
        else:
            raise ImproperlyConfigured(
                f"Field {field_name} of {self.__class__.__name__} defines an invalid value for 'q'.\n"
                f"Use FilterLookup annotation: {field_name}: Annotated[{field_info.annotation}, FilterLookup('lookup')]\n"
                f"Alternatively, you can implement {self.__class__.__name__}.filter_{field_name} that must return a Q expression for that field"
            )

    def _connect_fields(self) -> Q:
        q = Q()
        class_ignore_none = self.model_config.get("ignore_none", DEFAULT_IGNORE_NONE)
        for field_name, field_info in self.__class__.model_fields.items():
            filter_value = getattr(self, field_name)

            # class-level ignore_none set to False (non-default) takes precedence over field-level ignore_none
            if class_ignore_none is False:
                ignore_none = False
            else:
                field_ignore_none = self._get_field_ignore_none(field_name, field_info)
                if field_ignore_none is not None:
                    ignore_none = field_ignore_none
                else:
                    ignore_none = DEFAULT_IGNORE_NONE

            # Resolve Q expression for a field even if we skip it due to None value
            # So that improperly configured fields are easier to detect
            field_q = self._resolve_field_expression(
                field_name, filter_value, field_info
            )
            if filter_value is None and ignore_none:
                continue
            q = q._combine(  # type: ignore[attr-defined]
                field_q,
                self.model_config.get(
                    "expression_connector", DEFAULT_CLASS_LEVEL_EXPRESSION_CONNECTOR
                ),
            )

        return q

    def _get_from_deprecated_field_extra(
        self, field_name: str, field_info: FieldInfo, attr: str
    ) -> Union[Any, None]:
        """
        Backward-compatible shim which looks up filtering parameters in the Field's **extra kwargs.
        Consider removing this method in favor of FilterLookup annotation class.
        """
        field_extra = cast(dict, field_info.json_schema_extra) or {}
        value = field_extra.get(attr, NOT_SET)

        if value is not NOT_SET:
            warnings.warn(
                f"Using Pydantic Field with extra keyword arguments ('{attr}') "
                f"in field {self.__class__.__name__}.{field_name} is deprecated. Please use ninja.FilterLookup instead:\n"
                f"  from typing import Annotated\n"
                f"  from ninja import FilterLookup, FilterSchema\n\n"
                f"  class {self.__class__.__name__}(FilterSchema):\n"
                f"    {field_name}: Annotated[Optional[...], FilterLookup(q='...', ...)] = None",
                DeprecationWarning,
                stacklevel=4,
            )
            return value
        return None
