from typing import Generator, List, Tuple
from ninja.params.models import TModel
from ninja.schema import NinjaGenerateJsonSchema
from ninja.types import DictStrAny


class ParameterExtractor:
    def __init__(self, ref_template, open_api_schema):
        self.ref_template = ref_template
        self.open_api_schema = open_api_schema


    def _extract_parameters(self, model: TModel) -> List[DictStrAny]:
        result = []

        schema = model.model_json_schema(
            ref_template=self.ref_template,
            schema_generator=NinjaGenerateJsonSchema,
        )

        required = set(schema.get("required", []))
        properties = schema["properties"]

        if "$defs" in schema:
            self.add_schema_definitions(schema["$defs"])

        for name, details in properties.items():
            is_required = name in required
            p_name: str
            p_schema: DictStrAny
            p_required: bool
            for p_name, p_schema, p_required in self.flatten_properties(
                name, details, is_required, schema.get("$defs", {})
            ):
                if not p_schema.get("include_in_schema", True):
                    continue

                param = {
                    "in": model.__ninja_param_source__,
                    "name": p_name,
                    "schema": p_schema,
                    "required": p_required,
                }

                # copy description from schema description to param description
                if "description" in p_schema:
                    param["description"] = p_schema["description"]
                if "examples" in p_schema:
                    param["examples"] = p_schema["examples"]
                elif "example" in p_schema:
                    param["example"] = p_schema["example"]
                if "deprecated" in p_schema:
                    param["deprecated"] = p_schema["deprecated"]

                result.append(param)

        return result

    def flatten_properties(
        self,
        prop_name: str,
        prop_details: DictStrAny,
        prop_required: bool,
        definitions: DictStrAny,
    ) -> Generator[Tuple[str, DictStrAny, bool], None, None]:
        """
        extracts all nested model's properties into flat properties
        (used f.e. in GET params with multiple arguments and models)
        """
        if "allOf" in prop_details:
            resolve_allOf(prop_details, definitions)
            if len(prop_details["allOf"]) == 1 and "enum" in prop_details["allOf"][0]:
                # is_required = "default" not in prop_details
                yield prop_name, prop_details, prop_required
            else:  # pragma: no cover
                # TODO: this code was for pydanitc 1.7+ ... <2.9 - check if this is still needed
                for item in prop_details["allOf"]:
                    yield from self.flatten_properties("", item, True, definitions)

        elif "items" in prop_details and "$ref" in prop_details["items"]:
            def_name = prop_details["items"]["$ref"].rsplit("/", 1)[-1]
            prop_details["items"].update(definitions[def_name])
            del prop_details["items"]["$ref"]  # seems num data is there so ref not needed
            yield prop_name, prop_details, prop_required

        elif "$ref" in prop_details:
            def_name = prop_details["$ref"].split("/")[-1]
            definition = definitions[def_name]
            yield from self.flatten_properties(prop_name, definition, prop_required, definitions)

        elif "properties" in prop_details:
            required = set(prop_details.get("required", []))
            for k, v in prop_details["properties"].items():
                is_required = k in required
                yield from self.flatten_properties(k, v, is_required, definitions)
        else:
            yield prop_name, prop_details, prop_required
        
    def add_schema_definitions(self, definitions: dict) -> None:
        # TODO: check if schema["definitions"] are unique
        # if not - workaround (maybe use pydantic.schema.schema(models)) to process list of models
        # assert set(definitions.keys()) - set(self.schemas.keys()) == set()
        # ::TODO:: this is broken in interesting ways for by_alias,
        #     because same schema (name) can have different values
        self.open_api_schema.add_schema_definitions(definitions)

def resolve_allOf(details: DictStrAny, definitions: DictStrAny) -> None:
    """
    resolves all $ref's in 'allOf' section
    """
    for item in details["allOf"]:
        if "$ref" in item:
            def_name = item["$ref"].rsplit("/", 1)[-1]
            item.update(definitions[def_name])
            del item["$ref"]
