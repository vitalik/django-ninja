from typing import no_type_check

from django.db.models import Model as DjangoModel

from ninja.errors import ConfigError
from ninja.orm.factory import create_schema
from ninja.schema import ResolverMetaclass, Schema

_is_modelschema_class_defined = False


class ModelSchemaMetaclass(ResolverMetaclass):
    @no_type_check
    def __new__(
        mcs,
        name: str,
        bases: tuple,
        namespace: dict,
    ):
        cls = super().__new__(mcs, name, bases, namespace)
        for base in reversed(bases):
            if (
                _is_modelschema_class_defined
                and issubclass(base, ModelSchema)
                and base == ModelSchema
            ):
                try:
                    config = namespace["Config"]
                except KeyError:
                    raise ConfigError(
                        f"ModelSchema class '{name}' requires a 'Config' subclass"
                    )

                assert issubclass(config.model, DjangoModel)

                fields = getattr(config, "model_fields", None)
                exclude = getattr(config, "model_exclude", None)

                if not fields and not exclude:
                    raise ConfigError(
                        "Creating a ModelSchema without either the 'model_fields' attribute"
                        " or the 'model_exclude' attribute is prohibited"
                    )

                if fields == "__all__":
                    fields = None
                    # ^ when None is passed to create_schema - all fields are selected

                custom_fields = []
                annotations = namespace.get("__annotations__", {})
                for attr_name, type in annotations.items():
                    if attr_name.startswith("_"):
                        continue
                    default = namespace.get(attr_name, ...)
                    custom_fields.append((attr_name, type, default))

                # cls.__doc__ = namespace.get("__doc__", config.model.__doc__)
                cls.__fields__ = {}  # forcing pydantic recreate

                # print(config.model, name, fields, exclude, "!!")

                model_schema = create_schema(
                    config.model,
                    name=name,
                    fields=fields,
                    exclude=exclude,
                    custom_fields=custom_fields,
                    base_class=cls,
                )
                model_schema.__doc__ = cls.__doc__
                return model_schema

        return cls


class ModelSchema(Schema, metaclass=ModelSchemaMetaclass):
    pass


_is_modelschema_class_defined = True
