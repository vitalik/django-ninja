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
from inspect import getattr_static
from operator import attrgetter
from typing import Any, Type, TypeVar

import pydantic
from django.db.models import Manager, QuerySet
from django.db.models.fields.files import FieldFile
from pydantic import BaseModel, Field, validator
from pydantic.utils import GetterDict

pydantic_version = list(map(int, pydantic.VERSION.split(".")[:2]))
assert pydantic_version >= [1, 6], "Pydantic 1.6+ required"

__all__ = ["BaseModel", "Field", "validator", "DjangoGetter", "Schema"]

S = TypeVar("S", bound="Schema")


class DjangoGetter(GetterDict):
    __slots__ = ("_obj", "_schema_cls")

    def __init__(self, obj: Any, schema_cls: "Type[Schema]" = None):
        self._obj = obj
        self._schema_cls = schema_cls

    def _fake_instance(self) -> "Schema":
        """
        Generate a partial schema instance that can be used as the ``self``
        attribute of resolver functions.
        """
        getter_self = self

        class PartialSchema(Schema):
            def __getattr__(self, key: str) -> Any:
                value = getter_self[key]
                if getter_self._schema_cls:
                    field = getter_self._schema_cls.__fields__[key]
                    value = field.validate(value, values={}, loc=key, cls=None)[0]
                return value

        return PartialSchema()

    def __getitem__(self, key: str) -> Any:
        resolve_func = (
            getattr_static(self._schema_cls, f"resolve_{key}", None)
            if self._schema_cls
            else None
        )
        if resolve_func and isinstance(resolve_func, staticmethod):
            if not callable(resolve_func):
                # Before Python 3.10, the staticmethod is not callable directly.
                resolve_func = getattr(self._schema_cls, f"resolve_{key}")
            item = resolve_func(self._obj)
        elif resolve_func and callable(resolve_func):
            item = resolve_func(self._fake_instance(), self._obj)
        else:
            try:
                item = getattr(self._obj, key)
            except AttributeError:
                try:
                    item = attrgetter(key)(self._obj)
                except AttributeError as e:
                    raise KeyError(key) from e
        return self.format_result(item)

    def get(self, key: Any, default: Any = None) -> Any:
        try:
            return self[key]
        except KeyError:
            return default

    def format_result(self, result: Any) -> Any:
        if isinstance(result, Manager):
            return list(result.all())

        elif isinstance(result, getattr(QuerySet, "__origin__", QuerySet)):
            return list(result)

        elif isinstance(result, FieldFile):
            if not result:
                return None
            return result.url

        return result


class Schema(BaseModel):
    class Config:
        orm_mode = True
        getter_dict = DjangoGetter

    @classmethod
    def from_orm(cls: Type[S], obj: Any) -> S:
        # DjangoGetter also needs the class so it can find resolver methods.
        if not isinstance(obj, GetterDict):
            getter_dict = cls.__config__.getter_dict
            obj = (
                getter_dict(obj, cls)
                if issubclass(getter_dict, DjangoGetter)
                else getter_dict(obj)
            )
        return super().from_orm(obj)

    @classmethod
    def _decompose_class(cls, obj: Any) -> GetterDict:
        # This method has backported logic from Pydantic 1.9 and is no longer
        # needed once that is the minimum version.
        if isinstance(obj, GetterDict):
            return obj
        return super()._decompose_class(obj)
