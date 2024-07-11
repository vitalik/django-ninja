import datetime
from decimal import Decimal
from typing import (
    Any,
    Callable,
    Dict,
    List,
    Optional,
    Tuple,
    Type,
    TypeVar,
    Union,
    cast,
    no_type_check,
)
from uuid import UUID

from django.db.models import Choices, ManyToManyField, Model
from django.db.models.fields import Field as DjangoField
from django.db.models.fields.related import RelatedField as DjangoRelatedField
from pydantic import IPvAnyAddress
from pydantic.fields import FieldInfo
from pydantic_core import PydanticUndefined, core_schema
from typing_extensions import Literal, TypeAlias

from ninja.schema import Schema
from ninja.types import DictStrAny

__all__ = ["create_m2m_link_type", "get_schema_field", "get_related_field_schema"]


# keep_lazy seems not needed as .title forces translation anyway
# https://github.com/vitalik/django-ninja/issues/774
# @keep_lazy_text
def title_if_lower(s: str) -> str:
    if s == s.lower():
        return s.title()
    return s


class AnyObject:
    @classmethod
    def __get_pydantic_core_schema__(
        cls, source: Any, handler: Callable[..., Any]
    ) -> Any:
        return core_schema.with_info_plain_validator_function(cls.validate)

    @classmethod
    def __get_pydantic_json_schema__(
        cls, schema: Any, handler: Callable[..., Any]
    ) -> DictStrAny:
        return {"type": "object"}

    @classmethod
    def validate(cls, value: Any, _: Any) -> Any:
        return value


PythonType: TypeAlias = object
DjangoFieldName: TypeAlias = str
TYPES: Dict[DjangoFieldName, Type[PythonType]] = {
    "AutoField": int,
    "BigAutoField": int,
    "BigIntegerField": int,
    "BinaryField": bytes,
    "BooleanField": bool,
    "CharField": str,
    "DateField": datetime.date,
    "DateTimeField": datetime.datetime,
    "DecimalField": Decimal,
    "DurationField": datetime.timedelta,
    "FileField": str,
    "FilePathField": str,
    "FloatField": float,
    "GenericIPAddressField": IPvAnyAddress,
    "IPAddressField": IPvAnyAddress,
    "IntegerField": int,
    "JSONField": AnyObject,
    "NullBooleanField": bool,
    "PositiveBigIntegerField": int,
    "PositiveIntegerField": int,
    "PositiveSmallIntegerField": int,
    "SlugField": str,
    "SmallAutoField": int,
    "SmallIntegerField": int,
    "TextField": str,
    "TimeField": datetime.time,
    "UUIDField": UUID,
    # postgres fields:
    "ArrayField": List,
    "CICharField": str,
    "CIEmailField": str,
    "CITextField": str,
    "HStoreField": Dict,
}

TModel = TypeVar("TModel")


@no_type_check
def create_m2m_link_type(type_: Type[TModel]) -> Type[TModel]:
    class M2MLink(type_):  # type: ignore
        @classmethod
        def __get_pydantic_core_schema__(cls, source, handler):
            return core_schema.with_info_plain_validator_function(cls._validate)

        @classmethod
        def __get_pydantic_json_schema__(cls, schema, handler):
            json_type = {
                int: "integer",
                str: "string",
                float: "number",
                UUID: "string",
            }[type_]
            return {"type": json_type}

        @classmethod
        def _validate(cls, v: Any, _):
            try:
                return v.pk  # when we output queryset - we have db instances
            except AttributeError:
                return type_(v)  # when we read payloads we have primakey keys

    return M2MLink


def get_schema_field(
    field: DjangoField,
    *,
    depth: int = 0,
    optional: bool = False,
    choices_exclude: Optional[List[str]] = None,
) -> Tuple[PythonType, FieldInfo]:
    "Returns pydantic field from django's model field"
    alias = None
    default: Any = ...
    default_factory = None
    description = None
    title = None
    max_length = None
    nullable = False
    python_type: Optional[Type[PythonType]] = None
    choices_exclude = choices_exclude or []

    if field.is_relation:
        if depth > 0:
            return get_related_field_schema(
                cast(DjangoRelatedField, field), depth=depth
            )

        related_model = cast(Model, field.related_model)
        assert related_model._meta.pk is not None, "Related model has no primary key"
        internal_type = related_model._meta.pk.get_internal_type()

        if not field.concrete and field.auto_created or field.null or optional:
            default = None
            nullable = True

        alias = getattr(field, "get_attname", None) and field.get_attname()

        pk_type = TYPES.get(internal_type, int)
        if field.one_to_many or field.many_to_many:
            m2m_type = create_m2m_link_type(pk_type)
            python_type = List[m2m_type]  # type: ignore
        else:
            python_type = pk_type

    else:
        _f_name, _f_path, _f_pos, field_options = field.deconstruct()
        blank = field_options.get("blank", False)
        null = field_options.get("null", False)
        max_length = field_options.get("max_length")
        choices = field_options.get("choices")

        if not choices or _f_name in choices_exclude:
            internal_type = field.get_internal_type()
            python_type = TYPES[internal_type]
        else:
            # Django 5.x compat: choices can be an enum
            if isinstance(choices, type) and issubclass(choices, Choices):
                choices = choices.choices
            # Python 3.8 compat: can't unpack inline
            choice_list = [c[0] for c in choices]
            python_type = Literal[tuple(choice_list)]  # type: ignore

        if field.primary_key or blank or null or optional:
            default = None
            nullable = True

        if field.has_default():
            if callable(field.default):
                default_factory = field.default
            elif isinstance(field.default, Choices):
                default = field.default.value
            else:
                default = field.default

    if default_factory:
        default = PydanticUndefined

    if nullable:
        python_type = Union[python_type, None]  # type: ignore

    description = str(field.help_text) or None
    title = title_if_lower(str(field.verbose_name))

    return (
        python_type,
        FieldInfo(
            default=default,
            alias=alias,
            validation_alias=alias,
            serialization_alias=alias,
            default_factory=default_factory,
            title=title,
            description=description,
            max_length=max_length,
        ),
    )


def get_related_field_schema(
    field: DjangoRelatedField, *, depth: int
) -> Tuple[Type[Schema], FieldInfo]:
    from ninja.orm import create_schema

    model = cast(Type[Model], field.related_model)
    schema = create_schema(model, depth=depth - 1)
    default: Any = ...
    if not field.concrete and field.auto_created or field.null:
        default = None
    if isinstance(field, ManyToManyField):
        schema = List[schema]  # type: ignore

    return (
        schema,
        FieldInfo(
            default=default,
            description=str(field.help_text),
            title=title_if_lower(str(field.verbose_name)),
        ),
    )
