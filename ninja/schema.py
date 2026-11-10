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

import datetime
import decimal
import uuid
import warnings
from functools import lru_cache
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
    no_type_check,
)

import pydantic
from django.db.models import Manager, QuerySet
from django.db.models.fields.files import FieldFile
from django.template import Variable, VariableDoesNotExist
from pydantic import (
    AliasChoices,
    AliasPath,
    BaseModel,
    ConfigDict,
    Field,
    ValidationInfo,
    model_validator,
)
from pydantic._internal._model_construction import ModelMetaclass
from pydantic.functional_validators import ModelWrapValidatorHandler
from pydantic.json_schema import GenerateJsonSchema, JsonSchemaValue
from pydantic_core import InitErrorDetails, ValidationError
from typing_extensions import dataclass_transform

from ninja.errors import ConfigError
from ninja.signature.utils import get_args_names, has_kwargs
from ninja.types import DictStrAny

pydantic_version = list(map(int, pydantic.VERSION.split(".")[:2]))
assert pydantic_version >= [2, 0], "Pydantic 2.0+ required"

__all__ = ["BaseModel", "Field", "Schema"]

S = TypeVar("S", bound="Schema")


_MISSING: Any = object()

# Values of exactly these types never need converting, which lets the common
# case skip the isinstance() chain of _convert_result.
_PLAIN_TYPES = frozenset({
    str,
    int,
    float,
    bool,
    type(None),
    dict,
    list,
    tuple,
    bytes,
    datetime.datetime,
    datetime.date,
    datetime.time,
    datetime.timedelta,
    decimal.Decimal,
    uuid.UUID,
})

# Same list as from_attributes_applicable() in pydantic-core: pydantic does not
# read attributes from instances of types defined in these modules.
_NOT_ATTRIBUTE_SOURCES = frozenset({"builtins", "datetime", "collections"})

_QuerySetType: Any = getattr(QuerySet, "__origin__", QuerySet)

# One field: its name and the lookups pydantic tries for it, in order. Each
# lookup is a (key, rest) pair - ("name", ()) for a plain alias or the field
# name, ("boss", ("first_name",)) for AliasPath("boss", "first_name").
FieldLookups = Tuple[str, Tuple[Tuple[Any, Tuple[Any, ...]], ...]]


def _convert_result(result: Any) -> Any:
    if isinstance(result, Manager):
        return list(result.all())

    elif isinstance(result, _QuerySetType):
        return list(result)

    if callable(result):
        return result()

    elif isinstance(result, FieldFile):
        if not result:
            return None
        return result.url

    return result


@lru_cache(maxsize=None)
def _get_variable(key: str) -> Optional[Variable]:
    variable = Variable(key)
    if variable.lookups is None:
        # Variable comes from the template language, so it parses constants as
        # well as lookups: "0" and "1.5" are numbers, "'x'" is a string. These
        # have no lookups, and resolve() returns the constant without touching
        # the object. A field with alias="0" would then be "found" with the
        # value 0. Treat it as missing instead, so that the field name or the
        # default is used.
        return None
    return variable


def _resolve_variable(obj: Any, key: Any) -> Any:
    """
    Called when `obj` has no attribute `key`: dotted lookups
    (alias="boss.first_name") via django's template Variable.
    """
    if "." not in key:
        # A single name: all that Variable would still try is obj[key]. Doing
        # it here skips Variable's dir(obj) call, which is slow on a model
        # instance and runs for every alias that is not an attribute
        # (alias_generator=to_camel + populate_by_name).
        if key.isdigit():
            return _MISSING
        try:
            return obj[key]
        except Exception:
            return _MISSING
    variable = _get_variable(key)
    if variable is None:
        return _MISSING
    try:
        return variable.resolve(obj)
    except (VariableDoesNotExist, AttributeError):
        # AttributeError: django re-raises the one coming from a property
        return _MISSING


def _build_lookups(cls: Any) -> Tuple[FieldLookups, ...]:
    config = cls.model_config
    by_alias = config.get("validate_by_alias", True)
    by_name = bool(config.get("validate_by_name") or config.get("populate_by_name"))
    result = []
    for name, field in cls.model_fields.items():
        lookups: List[Tuple[Any, Tuple[Any, ...]]] = []
        alias = field.validation_alias
        if alias is None:
            alias = field.alias
        if alias is not None and by_alias:
            choices = alias.choices if isinstance(alias, AliasChoices) else [alias]
            for choice in choices:
                if isinstance(choice, AliasPath):
                    lookups.append((choice.path[0], tuple(choice.path[1:])))
                else:
                    lookups.append((choice, ()))
        if alias is None or by_name or not by_alias:
            if (name, ()) not in lookups:
                lookups.append((name, ()))
        result.append((name, tuple(lookups)))
    return tuple(result)


class _Nested(Dict[Any, Any]):
    "A dict built for an AliasPath lookup (as opposed to a source value)"


def _follow_path(value: Any, rest: Tuple[Any, ...]) -> Any:
    "The steps of an AliasPath after the first one, same rules as pydantic"
    for step in rest:
        if isinstance(step, str) and not isinstance(value, dict):
            value = getattr(value, step, _MISSING)
        elif isinstance(value, str):
            return _MISSING
        else:
            try:
                value = value[step]
            except Exception:
                return _MISSING
        if value is _MISSING:
            break
    return value


def _set_path(
    data: Dict[Any, Any], key: Any, rest: Tuple[Any, ...], value: Any
) -> None:
    target = data.setdefault(key, _Nested())
    if not isinstance(target, _Nested):
        raise ConfigError(
            f"AliasPath{(key, *rest)!r} can't be combined with another field "
            f"that reads {key!r} when validating from an object"
        )
    for step in rest[:-1]:
        target = target.setdefault(step, _Nested())
    target[rest[-1]] = value


def _extract(
    obj: Any,
    fields: Tuple[FieldLookups, ...],
    resolvers: Dict[str, "Resolver"],
    context: Any,
    title: str,
) -> Dict[Any, Any]:
    """
    Reads the fields of a schema from `obj` into a plain dict, keyed the way
    pydantic is going to look them up.

    `obj` is a dict only when the schema has resolvers, or the dict has values
    to convert. A plain dict is copied, so keys that are not fields stay
    visible to pydantic (extra="forbid" / "allow").
    """
    is_dict = isinstance(obj, dict)
    data: Dict[Any, Any] = dict(obj) if obj.__class__ is dict else {}
    errors: List[InitErrorDetails] = []
    for name, lookups in fields:
        for key, rest in lookups:
            try:
                if key in resolvers:
                    value = resolvers[key](obj, context)
                elif is_dict:
                    value = obj.get(key, _MISSING)
                    if value is _MISSING:
                        continue
                else:
                    try:
                        value = getattr(obj, key)
                    except AttributeError:
                        value = _resolve_variable(obj, key)
                        if value is _MISSING:
                            continue
                if value.__class__ not in _PLAIN_TYPES:
                    value = _convert_result(value)
                if rest:
                    found = _follow_path(value, rest)
                    if found is _MISSING:
                        continue
                    if not is_dict:  # for a dict pydantic follows the path itself
                        _set_path(data, key, rest, found)
                        break
                data[key] = value
                break
            except ConfigError:
                raise
            except Exception as e:
                # The error pydantic reports when reading an attribute fails
                errors.append({
                    "type": "get_attribute_error",
                    "loc": (name,),
                    "input": obj,
                    "ctx": {"error": f"{type(e).__name__}: {e}"},
                })
                break
    if errors:
        raise ValidationError.from_exception_data(title, errors)
    return data


class Resolver:
    __slots__ = ("_func", "_static", "_takes_context")
    _static: bool
    _func: Any
    _takes_context: bool

    def __init__(self, func: Union[Callable, staticmethod]):
        if isinstance(func, staticmethod):
            self._static = True
            self._func = func.__func__
        else:
            self._static = False
            self._func = func

        arg_names = get_args_names(self._func)
        self._takes_context = has_kwargs(self._func) or "context" in arg_names

    def __call__(self, obj: Any, context: Any = None) -> Any:
        if self._static:
            if self._takes_context:
                return self._func(obj, context=context)
            return self._func(obj)
        raise NotImplementedError(
            "Non static resolves are not supported yet"
        )  # pragma: no cover
        # return self._func(self._fake_instance(getter), getter._obj)

    # def _fake_instance(self, getter: Any) -> "Schema":
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


@dataclass_transform(kw_only_default=True, field_specifiers=(Field,))
class ResolverMetaclass(ModelMetaclass):
    _ninja_resolvers: Dict[str, Resolver]
    _ninja_lookups: Tuple[FieldLookups, ...]

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
    model_config = ConfigDict(from_attributes=True)

    @model_validator(mode="wrap")
    @classmethod
    def _run_root_validator(
        cls, values: Any, handler: ModelWrapValidatorHandler[S], info: ValidationInfo
    ) -> Any:
        values_cls = values.__class__
        resolvers = cls._ninja_resolvers
        if values_cls is dict:
            if not resolvers and _PLAIN_TYPES.issuperset(map(type, values.values())):
                # Nothing for us to do (e.g. a parsed request body)
                return handler(values)
        elif values_cls.__module__ in _NOT_ATTRIBUTE_SOURCES and not isinstance(
            values, dict
        ):
            # str, int, list, None ... pydantic does not read attributes from
            # these, and reports the proper error.
            return handler(values)

        fields_set = None
        if isinstance(values, cls):
            if handler.__class__.__name__ == "AssignmentValidatorCallable":
                # validate_assignment: `values` is the instance being assigned
                # to, handler() validates and sets that one attribute on it.
                # (pydantic 2.12+ could tell this from info.field_name being
                # set while info.data is None, older versions can not.)
                return handler(values)
            # An instance of this Schema (e.g. nested in another schema, or an
            # item of a List[...] response) is rebuilt like any other object, so
            # its values are re-validated and resolvers run with the current
            # context. Values that never went through validation
            # (model_construct, plain attribute assignment) can't reach the
            # output unfiltered that way.
            # Its model_fields_set is carried over, so exclude_unset keeps
            # working for nested schemas (#939).
            fields_set = values.model_fields_set & cls.model_fields.keys()

        fields = cls.__dict__.get("_ninja_lookups")
        if fields is None:
            fields = _build_lookups(cls)
            cls._ninja_lookups = fields

        result = handler(
            _extract(values, fields, resolvers, info.context, cls.__name__)
        )
        if fields_set is not None:
            object.__setattr__(result, "__pydantic_fields_set__", fields_set)
        return result

    @classmethod
    def from_orm(cls: Type[S], obj: Any, **kw: Any) -> S:
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


class _DeprecatedDjangoGetter:
    """
    Schema no longer wraps its input, so validators never receive an instance
    of this class. It is kept so that `from ninja.schema import DjangoGetter`
    and `isinstance(values, DjangoGetter)` checks keep working.
    """


def __getattr__(name: str) -> Any:
    if name == "DjangoGetter":
        warnings.warn(
            "DjangoGetter is deprecated: Schema validators now receive the input "
            "data itself (a dict), not a DjangoGetter wrapper",
            DeprecationWarning,
            stacklevel=2,
        )
        return _DeprecatedDjangoGetter
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
