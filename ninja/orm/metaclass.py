from typing import Any, List, Optional, Union, no_type_check

from django.db.models import Model as DjangoModel
from pydantic.dataclasses import dataclass

from ninja.conf import settings
from ninja.errors import ConfigError
from ninja.orm.factory import create_schema
from ninja.schema import ResolverMetaclass, Schema

_is_modelschema_class_defined = False


@dataclass
class MetaConf:
    model: Any
    fields: Optional[List[str]] = None
    exclude: Union[List[str], str, None] = None
    fields_optional: Union[List[str], str, None] = None
    nullable_type: Any = settings.NULLABLE_FIELD_UNION_TYPE
    nullable_value: Any = settings.NULLABLE_FIELD_DEFAULT_VALUE

    @staticmethod
    def from_schema_class(name: str, namespace: dict) -> "MetaConf":
        if "Config" in namespace:
            raise ConfigError(  # pragma: no cover
                "The use of `Config` class is removed for ModelSchema, use 'Meta' instead",
            )
        if "Meta" in namespace:
            meta = namespace["Meta"]
            model = meta.model
            fields = getattr(meta, "fields", None)
            exclude = getattr(meta, "exclude", None)
            optional_fields = getattr(meta, "fields_optional", None)
            nullable_type = getattr(
                meta, "nullable_type", settings.NULLABLE_FIELD_UNION_TYPE
            )
            nullable_value = getattr(
                meta, "nullable_value", settings.NULLABLE_FIELD_DEFAULT_VALUE
            )

        else:
            raise ConfigError(f"ModelSchema class '{name}' requires a 'Meta' subclass")

        assert issubclass(model, DjangoModel)

        if not fields and not exclude:
            raise ConfigError(
                "Creating a ModelSchema without either the 'fields' attribute"
                " or the 'exclude' attribute is prohibited"
            )

        if fields == "__all__":
            fields = None
            # ^ when None is passed to create_schema - all fields are selected

        return MetaConf(
            model=model,
            fields=fields,
            exclude=exclude,
            fields_optional=optional_fields,
            nullable_type=nullable_type,
            nullable_value=nullable_value,
        )


class ModelSchemaMetaclass(ResolverMetaclass):
    @no_type_check
    def __new__(
        mcs,
        name: str,
        bases: tuple,
        namespace: dict,
        **kwargs,
    ):
        cls = super().__new__(
            mcs,
            name,
            bases,
            namespace,
            **kwargs,
        )
        for base in reversed(bases):
            if (
                _is_modelschema_class_defined
                and issubclass(base, ModelSchema)
                and base == ModelSchema
            ):
                meta_conf = MetaConf.from_schema_class(name, namespace)

                custom_fields = []
                annotations = namespace.get("__annotations__", {})
                for attr_name, type in annotations.items():
                    if attr_name.startswith("_"):
                        continue
                    default = namespace.get(attr_name, ...)
                    custom_fields.append((attr_name, type, default))

                # # cls.__doc__ = namespace.get("__doc__", config.model.__doc__)
                # cls.__fields__ = {}  # forcing pydantic recreate
                # # assert False, "!! cls.model_fields"

                # print(config.model, name, fields, exclude, "!!")

                model_schema = create_schema(
                    meta_conf.model,
                    name=name,
                    fields=meta_conf.fields,
                    exclude=meta_conf.exclude,
                    optional_fields=meta_conf.fields_optional,
                    custom_fields=custom_fields,
                    nullable_type=meta_conf.nullable_type,
                    nullable_value=meta_conf.nullable_value,
                    base_class=cls,
                )
                model_schema.__doc__ = cls.__doc__
                return model_schema

        return cls


class ModelSchema(Schema, metaclass=ModelSchemaMetaclass):
    pass


_is_modelschema_class_defined = True
