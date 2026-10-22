import itertools
from typing import Any, Dict, Iterator, List, Optional, Set, Tuple, Type, Union, cast

from django.db.models import Field as DjangoField
from django.db.models import ManyToManyRel, ManyToOneRel, Model
from pydantic import create_model as create_pydantic_model

from ninja.errors import ConfigError
from ninja.orm.fields import get_schema_field
from ninja.schema import Schema

# MAYBE:
# Schema = create_schema(Model, exclude=['id'])
#
# @api.post
# def operation_create(request, payload: Schema):
#     orm_instance = payload.orm.apply(Model())
#     orm_instance.save()
#
# @api.post("/{id}")
# def operation_edit(request, id: int, payload: Schema):
#     orm_instance = payload.orm.apply(Model.objects.get(id=id))
#     orm_instance.save()

__all__ = ["SchemaFactory", "factory", "create_schema"]


def copy_field_info_without_alias(field_info: Any) -> Any:
    """Return the FieldInfo with its aliases cleared.

    Used when a relation field is exposed under its attname
    (`user_id`): the schema attribute name already *is* the model
    attribute to read and the key to emit, so the `user` -> `user_id`
    alias indirection that get_schema_field sets up would point
    pydantic at a second, wrong indirection. The FieldInfo is created
    fresh by get_schema_field for each call, so clearing the alias
    attributes on it cannot leak into other schemas.
    """
    field_info.alias = None
    field_info.validation_alias = None
    field_info.serialization_alias = None
    field_info.alias_priority = None
    return field_info

SchemaKey = Tuple[Type[Model], str, int, str, str, str, str]


class SchemaFactory:
    def __init__(self) -> None:
        self.schemas: Dict[SchemaKey, Type[Schema]] = {}
        self.schema_names: Set[str] = set()

    def create_schema(
        self,
        model: Type[Model],
        *,
        name: str = "",
        depth: int = 0,
        fields: Optional[List[str]] = None,
        exclude: Optional[List[str]] = None,
        optional_fields: Optional[List[str]] = None,
        custom_fields: Optional[List[Tuple[str, Any, Any]]] = None,
        base_class: Type[Schema] = Schema,
    ) -> Type[Schema]:
        name = name or model.__name__

        if fields and exclude:
            raise ConfigError("Only one of 'fields' or 'exclude' should be set.")

        key = self.get_key(
            model, name, depth, fields, exclude, optional_fields, custom_fields
        )
        if key in self.schemas:
            return self.schemas[key]

        model_fields_list = list(self._selected_model_fields(model, fields, exclude))
        if optional_fields:
            if optional_fields == "__all__":
                optional_fields = [name for name, _fld in model_fields_list]

        definitions = {}
        for def_name, fld in model_fields_list:
            # A field selected by its attname (e.g. `user_id` for the
            # `user` ForeignKey) exposes the raw key value: it always
            # uses the depth-0 (flat) schema field, and its name *is*
            # the attribute pydantic should read, so the attname alias
            # that get_schema_field attaches is dropped.
            by_attname = def_name != fld.name
            python_type, field_info = get_schema_field(
                fld,
                depth=0 if by_attname else depth,
                optional=optional_fields
                and (def_name in optional_fields or fld.name in optional_fields),
            )
            if by_attname:
                field_info = copy_field_info_without_alias(field_info)
            definitions[def_name] = (python_type, field_info)

        if custom_fields:
            for fld_name, python_type, field_info in custom_fields:
                # if not isinstance(field_info, FieldInfo):
                #     field_info = Field(field_info)
                definitions[fld_name] = (python_type, field_info)

        if name in self.schema_names:
            name = self._get_unique_name(name)

        schema: Type[Schema] = create_pydantic_model(
            name,
            __config__=None,
            __base__=base_class,
            __module__=base_class.__module__,
            __validators__={},
            **definitions,
        )  # type: ignore
        # __model_name: str,
        # *,
        # __config__: ConfigDict | None = None,
        # __base__: None = None,
        # __module__: str = __name__,
        # __validators__: dict[str, AnyClassMethod] | None = None,
        # __cls_kwargs__: dict[str, Any] | None = None,
        # **field_definitions: Any,
        self.schemas[key] = schema
        self.schema_names.add(name)
        return schema

    def get_key(
        self,
        model: Type[Model],
        name: str,
        depth: int,
        fields: Union[str, List[str], None],
        exclude: Optional[List[str]],
        optional_fields: Optional[Union[List[str], str]],
        custom_fields: Optional[List[Tuple[str, str, Any]]],
    ) -> SchemaKey:
        "returns a hashable value for all given parameters"
        # TODO: must be a test that compares all kwargs from init to get_key
        return (
            model,
            name,
            depth,
            str(fields),
            str(exclude),
            str(optional_fields),
            str(custom_fields),
        )

    def _get_unique_name(self, name: str) -> str:
        "Returns a unique name by adding counter suffix"
        for num in itertools.count(start=2):  # pragma: no branch
            result = f"{name}{num}"
            if result not in self.schema_names:
                break
        return result

    def _selected_model_fields(
        self,
        model: Type[Model],
        fields: Optional[List[str]] = None,
        exclude: Optional[List[str]] = None,
    ) -> Iterator[Tuple[str, DjangoField]]:
        """Returns iterator of (schema name, model field) pairs based on
        `exclude` or `fields` arguments.

        Besides field names, the attname of a concrete relation field
        (e.g. `user_id` for a `user` ForeignKey) is accepted everywhere
        a field name is: in `fields` it selects the field under its
        attname, in `exclude` it excludes the underlying field.
        """
        all_fields: Dict[str, Tuple[str, DjangoField]] = {}
        for f in self._model_fields(model):
            all_fields[f.name] = (f.name, f)
            attname = getattr(f, "attname", None)
            if attname and attname != f.name:
                all_fields[attname] = (attname, f)

        if not fields and not exclude:
            seen = set()
            for name, f in all_fields.values():
                if f.name not in seen:
                    seen.add(f.name)
                    yield name, f

        invalid_fields = (set(fields or []) | set(exclude or [])) - all_fields.keys()
        if invalid_fields:
            raise ConfigError(
                f"DjangoField(s) {invalid_fields} are not in model {model}"
            )

        if fields:
            for name in fields:
                yield all_fields[name]
        if exclude:
            excluded = {all_fields[name][1].name for name in exclude}
            seen = set()
            for _name, f in all_fields.values():
                if f.name not in excluded and f.name not in seen:
                    seen.add(f.name)
                    yield f.name, f

    def _model_fields(self, model: Type[Model]) -> Iterator[DjangoField]:
        "returns iterator with all the fields that can be part of schema"
        for fld in model._meta.get_fields():
            if isinstance(fld, (ManyToOneRel, ManyToManyRel)):
                # skipping relations
                continue
            yield cast(DjangoField, fld)


factory = SchemaFactory()

create_schema = factory.create_schema
