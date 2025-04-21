import warnings
from dataclasses import asdict
from typing import Any, List, Literal, Optional, Type, Union, no_type_check

from django.db.models import Model as DjangoModel
from pydantic.dataclasses import dataclass

from ninja.errors import ConfigError
from ninja.orm.factory import factory
from ninja.schema import ResolverMetaclass, Schema


@dataclass
class MetaConf:
    """
    Mirros the relevant arguments for create_schema

    model: Django model being used to create the Schema
    fields: List of field names in the model to use. Defaults to '__all__' which includes all fields
    exclude: List of field names to exclude
    optional_fields: List of field names which will be optional, can also take '__all__'
    depth: If > 0 schema will also be created for the nested ForeignKeys and Many2Many (with the provided depth of lookup)
    primary_key_optional: Defaults to True, controls if django's primary_key=True field in the provided model is required

    fields_optional: same as optional_fields, deprecated in order to match `create_schema()` API
    """

    model: Optional[Type[DjangoModel]] = None
    fields: Union[List[str], Literal["__all__"], Literal["__UNSET__"], None] = (
        "__UNSET__"
    )
    exclude: Union[List[str], str, None] = None
    optional_fields: Union[List[str], Literal["__all__"], None] = None
    depth: int = 0
    primary_key_optional: bool = True
    # deprecated
    fields_optional: Union[
        List[str], Literal["__all__"], None, Literal["__UNSET__"]
    ] = "__UNSET__"

    @classmethod
    def from_class_namepace(cls, name: str, namespace: dict) -> Union["MetaConf", None]:
        """Check namespace for Meta or Config and create MetaConf from those classes or return None"""
        conf = None
        if "Meta" in namespace:
            conf = cls.from_meta(namespace["Meta"])
        elif "Config" in namespace:
            conf = cls.from_config(namespace["Config"])
            if not conf:
                # No model so this isn't a "ModelSchema" config
                return None
            warnings.warn(
                "The use of `Config` class is deprecated for ModelSchema, use 'Meta' instead",
                DeprecationWarning,
                stacklevel=2,
            )

        if conf is None:
            return None

        if conf.model:
            if not conf.exclude and conf.fields == "__UNSET__":
                raise ConfigError("Specify either `exclude` or `fields`")
            elif conf.exclude and conf.fields == "__UNSET__":
                conf.fields = None

        if conf.fields_optional != "__UNSET__":
            if conf.optional_fields is not None:
                raise ConfigError(
                    "Specify either `fields_optional` or `optional_fields`. `fields_optional` is deprecated."
                )
            warnings.warn(
                "The use of `fields_optional` is deprecated. Use `optional_fields` instead to match `create_schema()` API",
                DeprecationWarning,
                stacklevel=2,
            )
            conf.optional_fields = conf.fields_optional

        return conf

    @staticmethod
    def from_config(config: Any) -> Union["MetaConf", None]:
        # FIXME: deprecate usage of Config to pass ORM options?
        confdict = {
            "model": getattr(config, "model", None),
            "fields": getattr(config, "model_fields", None),
            "exclude": getattr(config, "exclude", None),
            "optional_fields": getattr(config, "optional_fields", None),
            "depth": getattr(config, "depth", None),
            "primary_key_optional": getattr(config, "primary_key_optional", None),
            "fields_optional": getattr(config, "fields_optional", None),
        }
        if not confdict.get("model"):
            # this isn't a "ModelSchema" config class
            return None

        return MetaConf(**{k: v for k, v in confdict.items() if v is not None})

    @staticmethod
    def from_meta(meta: Any) -> Union["MetaConf", None]:
        confdict = {
            "model": getattr(meta, "model", None),
            "fields": getattr(meta, "fields", None),
            "exclude": getattr(meta, "exclude", None),
            "optional_fields": getattr(meta, "optional_fields", None),
            "depth": getattr(meta, "depth", None),
            "primary_key_optional": getattr(meta, "primary_key_optional", None),
            "fields_optional": getattr(meta, "fields_optional", None),
        }

        return MetaConf(**{k: v for k, v in confdict.items() if v is not None})


class ModelSchemaMetaclass(ResolverMetaclass):
    @no_type_check
    def __new__(
        mcs,
        name: str,
        bases: tuple,
        namespace: dict,
        **kwargs,
    ):
        namespace[
            "__ninja_meta__"
        ] = {}  # there might be a better place than __ninja_meta__?
        meta_conf = MetaConf.from_class_namepace(name, namespace)

        if meta_conf:
            meta_conf = asdict(meta_conf)
            # fields_optional is deprecated
            del meta_conf["fields_optional"]

            # update meta_conf with bases
            combined = {}
            for base in reversed(bases):
                combined.update(getattr(base, "__ninja_meta__", {}))
            combined.update(**meta_conf)
            namespace["__ninja_meta__"] = combined
            if namespace["__ninja_meta__"]["model"]:
                fields = factory.convert_django_fields(**namespace["__ninja_meta__"])
                for field, val in fields.items():
                    # if the field exists on the Schema, we don't overwrite it
                    if not namespace.get("__annotations__", {}).get(field):
                        # set type
                        namespace.setdefault("__annotations__", {})[field] = val[0]
                        # and default value
                        namespace[field] = val[1]

            del namespace["Meta"]  # clean up the space, might not be needed

        elif name != "ModelSchema":
            raise ConfigError(
                f"ModelSchema class '{name}' requires a 'Meta' (or a 'Config') subclass"
            )

        cls = super().__new__(
            mcs,
            name,
            bases,
            namespace,
            **kwargs,
        )
        return cls


class ModelSchema(Schema, metaclass=ModelSchemaMetaclass):
    @no_type_check
    def __new__(cls, *args, **kwargs):
        if not cls.__ninja_meta__.get("model"):
            raise ConfigError(
                f"No model set for class '{cls.__name__}' in the Meta hierarchy"
            )
        return super().__new__(cls)
