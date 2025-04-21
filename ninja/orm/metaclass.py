import warnings
from inspect import getmembers
from typing import List, Optional, Type, Union, no_type_check

from django.db.models import Model as DjangoModel
from pydantic import AliasChoices, BaseModel, ConfigDict, Field, model_validator
from typing_extensions import Literal, Self

from ninja.errors import ConfigError
from ninja.orm.factory import factory
from ninja.schema import ResolverMetaclass, Schema


class MetaConf(BaseModel):
    """
    Mirrors the relevant arguments for create_schema

    model: Django model being used to create the Schema
    fields: List of field names in the model to use. Defaults to '__all__' which includes all fields
    exclude: List of field names to exclude
    optional_fields: List of field names which will be optional, can also take '__all__'
    depth: If > 0 schema will also be created for the nested ForeignKeys and Many2Many (with the provided depth of lookup)
    primary_key_optional: Defaults to True, controls if django's primary_key=True field in the provided model is required

    fields_optional: same as optional_fields, deprecated in order to match `create_schema()` API
    """

    model: Optional[Type[DjangoModel]] = None
    # aliased for Config
    fields: Union[List[str], Literal["__all__"], None] = Field(
        None, validation_alias=AliasChoices("fields", "model_fields")
    )
    exclude: Optional[List[str]] = None
    optional_fields: Union[List[str], Literal["__all__"], None] = None
    depth: int = 0
    primary_key_optional: Optional[bool] = None
    # deprecated
    fields_optional: Union[List[str], Literal["__all__"], None] = Field(
        default=None, exclude=True
    )

    model_config = ConfigDict(extra="forbid")

    @model_validator(mode="after")
    def check_fields(self) -> Self:
        if self.model and (
            (not self.exclude and not self.fields) or (self.exclude and self.fields)
        ):
            raise ValueError("Specify either `exclude` or `fields`")

        if self.fields_optional:
            if self.optional_fields is not None:
                raise ValueError(
                    "Use only `optional_fields`, `fields_optional` is deprecated."
                )
            warnings.warn(
                "The use of `fields_optional` is deprecated. Use `optional_fields` instead to match `create_schema()` API",
                DeprecationWarning,
                stacklevel=2,
            )
            self.optional_fields = self.fields_optional
        return self


class ModelSchemaMetaclass(ResolverMetaclass):
    @no_type_check
    def __new__(
        mcs,
        name: str,
        bases: tuple,
        namespace: dict,
        **kwargs,
    ):
        conf_class = None
        meta_conf = None

        if "Meta" in namespace:
            conf_class = namespace["Meta"]
        elif "Config" in namespace:
            conf_class = namespace["Config"]
            warnings.warn(
                "The use of `Config` class is deprecated for ModelSchema, use 'Meta' instead",
                DeprecationWarning,
                stacklevel=2,
            )

        if conf_class:
            conf_dict = {
                k: v for k, v in getmembers(conf_class) if not k.startswith("__")
            }
            meta_conf = MetaConf.model_validate(conf_dict)

        if meta_conf and meta_conf.model:
            meta_conf = meta_conf.model_dump(exclude_none=True)

            fields = factory.convert_django_fields(**meta_conf)
            for field, val in fields.items():
                # do not allow field to be defined both in the class and
                # explicitly through `Meta.fields` or implicitly through `Meta.excluded`
                if namespace.get("__annotations__", {}).get(field):
                    raise ConfigError(
                        f"'{field}' is defined in class body and in Meta.fields or implicitly in Meta.excluded"
                    )
                # set type
                namespace.setdefault("__annotations__", {})[field] = val[0]
                # and default value
                namespace[field] = val[1]

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
        if not getattr(getattr(cls, "Meta", {}), "model", None):
            raise ConfigError(f"No model set for class '{cls.__name__}'")
        return super().__new__(cls)
