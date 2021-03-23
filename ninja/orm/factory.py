from typing import Dict, Iterator, List, Optional, Tuple, Type, Union, cast

from django.db.models import Field, ManyToManyRel, ManyToOneRel, Model
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

SchemaKey = Tuple[Type[Model], str, int, str, str]


class SchemaFactory:
    def __init__(self) -> None:
        self.schemas: Dict[SchemaKey, Type[Schema]] = {}

    def create_schema(
        self,
        model: Type[Model],
        *,
        name: str = "",
        depth: int = 0,
        fields: Optional[List[str]] = None,
        exclude: Optional[List[str]] = None,
    ) -> Type[Schema]:
        name = name or model.__name__

        if fields and exclude:
            raise ConfigError("Only one of 'include' or 'exclude' should be set.")

        key = self.get_key(model, name, depth, fields, exclude)
        if key in self.schemas:
            return self.schemas[key]

        definitions = {}
        for fld in self._selected_model_fields(model, fields, exclude):
            python_type, field_info = get_schema_field(fld, depth=depth)
            definitions[fld.name] = (python_type, field_info)

        schema = cast(
            Type[Schema],
            create_pydantic_model(name, __base__=Schema, **definitions),  # type: ignore
        )
        self.schemas[key] = schema
        return schema

    def get_key(
        self,
        model: Type[Model],
        name: str,
        depth: int,
        fields: Union[str, List[str], None],
        exclude: Optional[List[str]],
    ) -> SchemaKey:
        "returns a hashable value for all given parameters"
        # TODO: must be a test that compares all kwargs from init to get_key
        return model, name, depth, str(fields), str(exclude)

    def _selected_model_fields(
        self,
        model: Type[Model],
        fields: Optional[List[str]] = None,
        exclude: Optional[List[str]] = None,
    ) -> Iterator[Field]:
        "Returns iterator for model fields based on `exclude` or `fields` arguments"
        all_fields = {f.name: f for f in self._model_fields(model)}

        if not fields and not exclude:
            for f in all_fields.values():
                yield f

        invalid_fields = (set(fields or []) | set(exclude or [])) - all_fields.keys()
        if invalid_fields:
            raise ConfigError(f"Field(s) {invalid_fields} are not in model.")

        if fields:
            for name in fields:
                yield all_fields[name]
        if exclude:
            for f in all_fields.values():
                if f.name not in exclude:
                    yield f

    def _model_fields(self, model: Type[Model]) -> Iterator[Field]:
        "returns iterator with all the fields that can be part of schema"
        for fld in model._meta.get_fields():
            if isinstance(fld, (ManyToOneRel, ManyToManyRel)):
                # skipping relations
                continue
            yield cast(Field, fld)


factory = SchemaFactory()

create_schema = factory.create_schema
