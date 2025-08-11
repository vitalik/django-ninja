import warnings
from typing import Any, Dict, Optional, TypeVar, Union, cast

from django.core.exceptions import ImproperlyConfigured
from django.db.models import Q, QuerySet
from pydantic import ConfigDict, Field
from pydantic.fields import FieldInfo
from typing_extensions import Literal

from .schema import Schema

DEFAULT_IGNORE_NONE = True
DEFAULT_CLASS_LEVEL_EXPRESSION_CONNECTOR = "AND"
DEFAULT_FIELD_LEVEL_EXPRESSION_CONNECTOR = "OR"

# XOR is available only in Django 4.1+: https://docs.djangoproject.com/en/4.1/ref/models/querysets/#xor
ExpressionConnector = Literal["AND", "OR", "XOR"]

T = TypeVar("T", bound=QuerySet)


def FilterField(
    default: Any = ...,
    *,
    q: Optional[Union[str, list]] = None,
    ignore_none: Optional[bool] = None,
    expression_connector: Optional[ExpressionConnector] = None,
    **kwargs: Any,
) -> Any:
    """Custom Field function for FilterSchema that properly handles filter-specific parameters."""
    json_schema_extra = kwargs.get("json_schema_extra", {})
    if isinstance(json_schema_extra, dict):
        if q is not None:
            json_schema_extra["q"] = q
        if ignore_none is not None:
            json_schema_extra["ignore_none"] = ignore_none
        if expression_connector is not None:
            json_schema_extra["expression_connector"] = expression_connector
    kwargs["json_schema_extra"] = json_schema_extra

    return Field(default, **kwargs)


class FilterSchema(Schema):
    model_config = ConfigDict(from_attributes=True)

    class Meta:
        # TODO: filters_ignore_none, filters_expression_connector
        ignore_none: bool = DEFAULT_IGNORE_NONE
        expression_connector: ExpressionConnector = cast(
            ExpressionConnector, DEFAULT_CLASS_LEVEL_EXPRESSION_CONNECTOR
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

    def _resolve_field_expression(
        self, field_name: str, field_value: Any, field: FieldInfo
    ) -> Q:
        func = getattr(self, f"filter_{field_name}", None)
        if callable(func):
            return func(field_value)  # type: ignore[no-any-return]

        field_extra = field.json_schema_extra or {}

        # Check if user is using pydantic Field with deprecated extra kwargs
        # This check is for backwards compatibility during transition period
        if hasattr(field, "extra") and field.extra:
            warnings.warn(
                f"Using pydantic Field with extra keyword arguments (q, ignore_none, expression_connector) "
                f"in field '{field_name}' is deprecated. Please use ninja.FilterField instead:\n"
                f"  from ninja import FilterField\n"
                f"  {field_name}: Optional[...] = FilterField(..., q='...', ignore_none=...)",
                DeprecationWarning,
                stacklevel=4,
            )

        q_expression = field_extra.get("q", None)  # type: ignore
        if not q_expression:
            return Q(**{field_name: field_value})
        elif isinstance(q_expression, str):
            if q_expression.startswith("__"):
                q_expression = f"{field_name}{q_expression}"
            return Q(**{q_expression: field_value})
        elif isinstance(q_expression, list):
            expression_connector = field_extra.get(  # type: ignore
                "expression_connector", DEFAULT_FIELD_LEVEL_EXPRESSION_CONNECTOR
            )
            q = Q()
            for q_expression_part in q_expression:
                q_expression_part = str(q_expression_part)
                if q_expression_part.startswith("__"):
                    q_expression_part = f"{field_name}{q_expression_part}"
                q = q._combine(  # type: ignore
                    Q(**{q_expression_part: field_value}),
                    expression_connector,
                )
            return q
        else:
            raise ImproperlyConfigured(
                f"Field {field_name} of {self.__class__.__name__} defines an invalid value under 'q' kwarg.\n"
                f"Define a 'q' kwarg as a string or a list of strings, each string corresponding to a database lookup you wish to filter against:\n"
                f"  {field_name}: {field.annotation} = Field(..., q='<here>')\n"
                f"or\n"
                f"  {field_name}: {field.annotation} = Field(..., q=['lookup1', 'lookup2', ...])\n"
                f"You can omit the field name and make it implicit by starting the lookup directly by '__'."
                f"Alternatively, you can implement {self.__class__.__name__}.filter_{field_name} that must return a Q expression for that field"
            )

    def _connect_fields(self) -> Q:
        q = Q()
        model_config = self._model_config()
        for field_name, field in self.__class__.model_fields.items():
            filter_value = getattr(self, field_name)
            field_extra = field.json_schema_extra or {}
            ignore_none = field_extra.get(  # type: ignore
                "ignore_none",
                model_config["ignore_none"],
            )

            # Resolve q for a field even if we skip it due to None value
            # So that improperly configured fields are easier to detect
            field_q = self._resolve_field_expression(field_name, filter_value, field)
            if filter_value is None and ignore_none:
                continue
            q = q._combine(field_q, model_config["expression_connector"])  # type: ignore

        return q

    @classmethod
    def _model_config(cls) -> Dict[str, Any]:
        return {
            "ignore_none": cls.Meta.ignore_none,
            "expression_connector": cls.Meta.expression_connector,
        }
