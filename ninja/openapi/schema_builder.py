from typing import Tuple
from ninja.params.models import TModel
from ninja.schema import NinjaGenerateJsonSchema
from ninja.types import DictStrAny
from pydantic.json_schema import JsonSchemaMode

class SchemaBuilder:
    def __init__(self, ref_template, open_api_schema):
        self.ref_template = ref_template
        self.open_api_schema = open_api_schema

    def _create_schema_from_model(
        self,
        model: TModel,
        by_alias: bool = True,
        remove_level: bool = True,
        mode: JsonSchemaMode = "validation",
    ) -> Tuple[DictStrAny, bool]:
        if hasattr(model, "__ninja_flatten_map__"):
            schema = self._flatten_schema(model)
        else:
            schema = model.model_json_schema(
                ref_template=self.ref_template,
                by_alias=by_alias,
                schema_generator=NinjaGenerateJsonSchema,
                mode=mode,
            ).copy()

        # move Schemas from definitions
        if schema.get("$defs"):
            self.open_api_schema.add_schema_definitions(schema.pop("$defs"))

        if remove_level and len(schema["properties"]) == 1:
            name, details = list(schema["properties"].items())[0]

            # ref = details["$ref"]
            required = name in schema.get("required", {})
            return details, required
        else:
            return schema, True
        
    def _flatten_schema(self, model: TModel) -> DictStrAny:
        params = self.open_api_schema.param_extractor._extract_parameters(model)
        flattened = {
            "title": model.__name__,  # type: ignore
            "type": "object",
            "properties": {p["name"]: p["schema"] for p in params},
        }
        required = [p["name"] for p in params if p["required"]]
        if required:
            flattened["required"] = required
        return flattened