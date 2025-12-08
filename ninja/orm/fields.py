import datetime
from decimal import Decimal
from typing import Any, Callable, Dict, List, Tuple, Type, TypeVar, Union, no_type_check
from uuid import UUID

from django.db.models import ManyToManyField
from django.db.models.fields import Field as DjangoField
from pydantic import IPvAnyAddress
from pydantic.fields import FieldInfo
from pydantic_core import PydanticUndefined, core_schema

from ninja.errors import ConfigError
from ninja.openapi.schema import OpenAPISchema
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


TYPES = {
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


def register_field(django_field: str, python_type: Any) -> None:
    TYPES[django_field] = python_type


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


@no_type_check
def get_schema_field(
    field: DjangoField, *, depth: int = 0, optional: bool = False
) -> Tuple:
    "Returns pydantic field from django's model field"

    alias = None
    max_length = None

    if field.is_relation:
        result = _handle_relation_field(field, depth=depth, optional=optional)

        if isinstance(result, tuple) and len(result) == 5:
            python_type, default, default_factory, nullable, alias = result
        else:
            return result

    else:
        python_type, default, default_factory, nullable, max_length = _handle_normal_field(
            field, optional=optional
        )

    if default_factory:
        default = PydanticUndefined

    if nullable:
        python_type = Union[python_type, None]

    description = field.help_text or None
    title = title_if_lower(field.verbose_name)

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


def _get_python_type(internal_type: str):
    try:
        return TYPES[internal_type]
    except KeyError as e:
        msg = [
            f"Do not know how to convert django field '{internal_type}'.",
            "Try from ninja.orm import register_field",
            f"register_field('{internal_type}', <your-python-type>)",
        ]
        raise ConfigError("\n".join(msg)) from e


def _should_be_nullable(*flags: bool) -> bool:
    return any(flags)


def _handle_relation_field(field, *, depth: int, optional: bool):
    if depth > 0:
        return get_related_field_schema(field, depth=depth)

    default = ...
    default_factory = None
    nullable = False
    alias = None

    internal_type = field.related_model._meta.pk.get_internal_type()

    if not field.concrete and field.auto_created or field.null or optional:
        default = None
        nullable = True

    alias = getattr(field, "get_attname", None) and field.get_attname()

    pk_type = _get_python_type(internal_type)

    if field.one_to_many or field.many_to_many:
        m2m_type = create_m2m_link_type(pk_type)
        python_type = List[m2m_type]  # type: ignore
    else:
        python_type = pk_type

    return python_type, default, default_factory, nullable, alias


def _handle_normal_field(field, *, optional: bool):
    default = ...
    default_factory = None
    nullable = False

    _f_name, _f_path, _f_pos, field_options = field.deconstruct()

    blank = field_options.get("blank", False)
    null = field_options.get("null", False)
    max_length = field_options.get("max_length")

    internal_type = field.get_internal_type()
    python_type = _get_python_type(internal_type)

    if _should_be_nullable(field.primary_key, blank, null, optional):
        default = None
        nullable = True

    if field.has_default():
        if callable(field.default):
            default_factory = field.default
        else:
            default = field.default

    return python_type, default, default_factory, nullable, max_length



@no_type_check
def get_related_field_schema(field: DjangoField, *, depth: int) -> Tuple[OpenAPISchema]:
    from ninja.orm import create_schema

    model = field.related_model
    schema = create_schema(model, depth=depth - 1)
    default = ...
    if not field.concrete and field.auto_created or field.null:
        default = None
    if isinstance(field, ManyToManyField):
        schema = List[schema]  # type: ignore

    return (
        schema,
        FieldInfo(
            default=default,
            description=field.help_text,
            title=title_if_lower(field.verbose_name),
        ),
    )
