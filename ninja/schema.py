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

        def resolve_initials(self, obj):
            return "".join(n[:1] for n in self.name.split())

"""
from typing import Any, Callable, Dict, Type, TypeVar, Union, no_type_check

import pydantic
from django.db.models import Manager, QuerySet
from django.db.models.fields.files import FieldFile
from django.template import Variable, VariableDoesNotExist
from pydantic import BaseModel, Field, model_validator, validator
from pydantic._internal._model_construction import ModelMetaclass
from pydantic.json_schema import (
    DEFAULT_REF_TEMPLATE,
    GenerateJsonSchema,
    JsonSchemaMode,
    JsonSchemaValue,
    model_json_schema,
)

from ninja.types import DictStrAny

pydantic_version = list(map(int, pydantic.VERSION.split(".")[:2]))
assert pydantic_version >= [2, 0], "Pydantic 2.0+ required"

__all__ = ["BaseModel", "Field", "validator", "DjangoGetter", "Schema"]

S = TypeVar("S", bound="Schema")


class DjangoGetter:
    __slots__ = ("_obj", "_schema_cls")

    def __init__(self, obj: Any, schema_cls: "Type[Schema]"):
        self._obj = obj
        self._schema_cls = schema_cls

    def __getattr__(self, key: str) -> Any:
        # if key.startswith("__pydantic"):
        #     return getattr(self._obj, key)

        resolver = self._schema_cls._ninja_resolvers.get(key)
        if resolver:
            value = resolver(getter=self)
        else:
            if isinstance(self._obj, dict):
                if key not in self._obj:
                    raise AttributeError(key)
                value = self._obj[key]
            else:
                try:
                    value = getattr(self._obj, key)
                except AttributeError:
                    try:
                        # value = attrgetter(key)(self._obj)
                        value = Variable(key).resolve(self._obj)
                        # TODO: Variable(key) __init__ is actually slower than
                        #       resolve - so it better be cached
                    except VariableDoesNotExist as e:
                        raise AttributeError(key) from e
        return self._convert_result(value)

    # def get(self, key: Any, default: Any = None) -> Any:
    #     try:
    #         return self[key]
    #     except KeyError:
    #         return default

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


class Resolver:
    __slots__ = ("_func", "_static")
    _static: bool
    _func: Any

    def __init__(self, func: Union[Callable, staticmethod]):
        if isinstance(func, staticmethod):
            self._static = True
            self._func = func.__func__
        else:
            self._static = False
            self._func = func

    def __call__(self, getter: DjangoGetter) -> Any:
        if self._static:
            return self._func(getter._obj)
        raise NotImplementedError(
            "Non static resolves are not supported yet"
        )  # pragma: no cover
        # return self._func(self._fake_instance(getter), getter._obj)

    # def _fake_instance(self, getter: DjangoGetter) -> "Schema":
    #     """
    #     Generate a partial schema instance that can be used as the ``self``
    #     attribute of resolver functions.
    #     """

    #     class PartialSchema(Schema):
    #         def __getattr__(self, key: str) -> Any:
    #             value = getattr(getter, key)
    #             field = getter._schema_cls.model_fields[key]
    #             value = field.validate(value, values={}, loc=key, cls=None)[0]
    #             return value

    #     return PartialSchema()


class ResolverMetaclass(ModelMetaclass):
    _ninja_resolvers: Dict[str, Resolver]

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

    @model_validator(mode="before")
    def run_root_validator(cls, values, info):
        values = DjangoGetter(values, cls)
        return values

    @classmethod
    def from_orm(cls: Type[S], obj: Any) -> S:
        return cls.model_validate(obj)

    def dict(self, *a, **kw):
        return self.model_dump(*a, **kw)

    @classmethod
    def schema(cls):
        return cls.model_json_schema()

    @classmethod
    def model_json_schema(
        cls,
        by_alias: bool = True,
        ref_template: str = DEFAULT_REF_TEMPLATE,
        schema_generator: type[GenerateJsonSchema] = NinjaGenerateJsonSchema,
        mode: JsonSchemaMode = "validation",
    ) -> DictStrAny:
        return model_json_schema(
            cls,
            by_alias=by_alias,
            ref_template=ref_template,
            schema_generator=schema_generator,
            mode=mode,
        )
