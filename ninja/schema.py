"""
Since "Model" word would be very confusing when used in django context, this
module basically makes an alias for it named "Schema" and adds extra whistles to
be able to work with django querysets and managers.

The schema is a bit smarter than a standard pydantic Model because it can handle
dotted attributes and resolver methods. For example::


    class UserSchema(User):
        name: str
        initials: str
        boss: str = Field(None, alias="boss.first_name")

        @staticmethod
        def resolve_name(obj):
            return f"{obj.first_name} {obj.last_name}"

"""

from __future__ import annotations

import warnings
from functools import partial
from typing import (
    Any,
    Callable,
    ClassVar,
    TypeVar,
    no_type_check,
)

import pydantic
from django.db.models import Manager, QuerySet
from django.db.models.fields.files import FieldFile
from django.template import Variable, VariableDoesNotExist
from pydantic import BaseModel, Field, ValidationInfo, model_validator, validator
from pydantic._internal._model_construction import ModelMetaclass
from pydantic.functional_validators import ModelWrapValidatorHandler
from pydantic.json_schema import GenerateJsonSchema, JsonSchemaValue
from typing_extensions import dataclass_transform

from ninja.constants import NOT_SET
from ninja.signature.utils import get_args_names, has_kwargs
from ninja.types import DictStrAny

pydantic_version = list(map(int, pydantic.VERSION.split(".")[:2]))
assert pydantic_version >= [2, 0], "Pydantic 2.0+ required"

__all__ = ["BaseModel", "Field", "validator", "DjangoGetter", "Schema"]

S = TypeVar("S", bound="Schema")


def dict_getter(key: str, obj: DjangoGetter) -> Any:
    if key not in obj._obj:
        raise AttributeError(key)
    return obj._obj[key]


def attr_getter(key: str, obj: DjangoGetter) -> Any:
    try:
        return Variable(key).resolve(obj._obj)
    except VariableDoesNotExist as e:
        raise AttributeError(key) from e


def resolver(resolve_func: Callable, _: str, obj: DjangoGetter) -> Any:
    return resolve_func(getter=obj)


def get_attr(key: str, obj: DjangoGetter) -> Any:
    return getattr(obj._obj, key)


class DjangoGetter:
    __slots__ = ("_obj", "_schema_cls", "_context", "__dict__", "_cache_key")
    _cache: ClassVar[dict[str, Callable]] = {}

    def __init__(self, obj: Any, schema_cls: type[S], context: Any = None) -> None:
        self._obj = obj
        self._schema_cls = schema_cls
        self._context = context
        self._cache_key = f"{self._schema_cls.__module__}.{self._schema_cls.__name__}.{self._obj.__class__.__name__}"

    def __getattr__(self, key: str) -> Any:
        cache_key = f"{self._cache_key}.{key}"
        if cache_key in DjangoGetter._cache:
            # Use cached function, if available.
            value = DjangoGetter._cache[cache_key](key, self)
            return self._convert_result(value)

        stored_resolver = self._schema_cls._ninja_resolvers.get(key)
        if stored_resolver:
            # Use resolver when provided for this key.
            value = stored_resolver(getter=self)
            # bind resolver of this key to the _cache
            DjangoGetter._cache[cache_key] = partial(resolver, stored_resolver)
            return self._convert_result(value)

        if isinstance(self._obj, dict):
            # Use dict lookup, faster than getattr
            value = dict_getter(key, self)
            DjangoGetter._cache[cache_key] = dict_getter
            return self._convert_result(value)

        value = getattr(self._obj, key, NOT_SET)
        if value is not NOT_SET:
            # If getattr worked, use that.
            DjangoGetter._cache[cache_key] = get_attr
            return self._convert_result(value)
        # Finally, fallback to attr_getter
        value = attr_getter(key, self)
        DjangoGetter._cache[cache_key] = attr_getter
        return self._convert_result(value)

    def _convert_result(self, result: Any) -> Any:
        if isinstance(result, Manager):
            return list(result.all())

        elif isinstance(result, getattr(QuerySet, "__origin__", QuerySet)):
            return list(result)

        if callable(result):
            return result()

        elif isinstance(result, FieldFile):
            if not result:
                return None
            return result.url

        return result

    def __repr__(self) -> str:
        return f"<DjangoGetter: {repr(self._obj)}>"


class Resolver:
    __slots__ = ("_func", "_static", "_takes_context")
    _static: bool
    _func: Any
    _takes_context: bool

    def __init__(self, func: Callable | staticmethod):
        if isinstance(func, staticmethod):
            self._static = True
            self._func = func.__func__
        else:
            self._static = False
            self._func = func

        arg_names = get_args_names(self._func)
        self._takes_context = has_kwargs(self._func) or "context" in arg_names

    def __call__(self, getter: DjangoGetter) -> Any:
        kwargs = {}
        if self._takes_context:
            kwargs["context"] = getter._context

        if self._static:
            return self._func(getter._obj, **kwargs)
        raise NotImplementedError(
            "Non static resolves are not supported yet"
        )  # pragma: no cover
        # return self._func(self._fake_instance(getter), getter._obj)


@dataclass_transform(kw_only_default=True, field_specifiers=(Field,))
class ResolverMetaclass(ModelMetaclass):
    _ninja_resolvers: dict[str, Resolver]

    @no_type_check
    def __new__(cls, name, bases, namespace, **kwargs):
        resolvers = {}

        for base in reversed(bases):
            base_resolvers = getattr(base, "_ninja_resolvers", None)
            if base_resolvers:
                resolvers.update(base_resolvers)
        for attr, resolve_func in namespace.items():
            if not attr.startswith("resolve_"):
                continue
            if (
                not callable(resolve_func)
                # A staticmethod isn't directly callable in Python <=3.9.
                and not isinstance(resolve_func, staticmethod)
            ):
                continue  # pragma: no cover
            resolvers[attr[8:]] = Resolver(resolve_func)

        result = super().__new__(cls, name, bases, namespace, **kwargs)
        result._ninja_resolvers = resolvers
        return result


class NinjaGenerateJsonSchema(GenerateJsonSchema):
    def default_schema(self, schema: Any) -> JsonSchemaValue:
        # Pydantic default actually renders null's and default_factory's
        # which really breaks swagger and django model callable defaults
        # so here we completely override behavior
        json_schema = self.generate_inner(schema["schema"])

        default = None
        if "default" in schema and schema["default"] is not None:
            default = self.encode_default(schema["default"])

        if "$ref" in json_schema:
            # Since reference schemas do not support child keys, we wrap the reference schema in a single-case allOf:
            result = {"allOf": [json_schema]}
        else:
            result = json_schema

        if default is not None:
            result["default"] = default

        return result


class Schema(BaseModel, metaclass=ResolverMetaclass):
    class Config:
        from_attributes = True  # aka orm_mode

    @model_validator(mode="wrap")
    @classmethod
    def _run_root_validator(
        cls, values: Any, handler: ModelWrapValidatorHandler[S], info: ValidationInfo
    ) -> Any:
        # If Pydantic intends to validate against the __dict__ of the immediate Schema
        # object, then we need to call `handler` directly on `values` before the conversion
        # to DjangoGetter, since any checks or modifications on DjangoGetter's __dict__
        # will not persist to the original object.
        forbids_extra = cls.model_config.get("extra") == "forbid"
        should_validate_assignment = cls.model_config.get("validate_assignment", False)
        if forbids_extra or should_validate_assignment:
            handler(values)

        values = DjangoGetter(values, cls, info.context)
        return handler(values)

    @classmethod
    def from_orm(cls: type[S], obj: Any, **kw: Any) -> S:
        return cls.model_validate(obj, **kw)

    def dict(self, *a: Any, **kw: Any) -> DictStrAny:
        "Backward compatibility with pydantic 1.x"
        return self.model_dump(*a, **kw)

    @classmethod
    def json_schema(cls) -> DictStrAny:
        return cls.model_json_schema(schema_generator=NinjaGenerateJsonSchema)

    @classmethod
    def schema(cls) -> DictStrAny:  # type: ignore
        warnings.warn(
            ".schema() is deprecated, use .json_schema() instead",
            DeprecationWarning,
            stacklevel=2,
        )
        return cls.json_schema()
