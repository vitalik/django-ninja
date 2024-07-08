import itertools
import re
from http.client import responses
from typing import TYPE_CHECKING, Any, Dict, Generator, List, Optional, Set, Tuple

from django.utils.termcolors import make_style

from ninja.constants import NOT_SET
from ninja.operation import Operation
from ninja.params.models import TModel, TModels
from ninja.schema import NinjaGenerateJsonSchema
from ninja.types import DictStrAny
from ninja.utils import normalize_path

if TYPE_CHECKING:
    from ninja import NinjaAPI  # pragma: no cover

REF_TEMPLATE: str = "#/components/schemas/{model}"

BODY_CONTENT_TYPES: Dict[str, str] = {
    "body": "application/json",
    "form": "application/x-www-form-urlencoded",
    "file": "multipart/form-data",
}


def get_schema(api: "NinjaAPI", path_prefix: str = "") -> "OpenAPISchema":
    openapi = OpenAPISchema(api, path_prefix)
    return openapi


bold_red_style = make_style(opts=("bold",), fg="red")


class OpenAPISchema(dict):
    def __init__(self, api: "NinjaAPI", path_prefix: str) -> None:
        self.api = api
        self.path_prefix = path_prefix
        self.schemas: DictStrAny = {}
        self.securitySchemes: DictStrAny = {}
        self.all_operation_ids: Set = set()
        extra_info = api.openapi_extra.get("info", {})
        super().__init__(
            [
                ("openapi", "3.1.0"),
                (
                    "info",
                    {
                        "title": api.title,
                        "version": api.version,
                        "description": api.description,
                        **extra_info,
                    },
                ),
                ("paths", self.get_paths()),
                ("components", self.get_components()),
                ("servers", api.servers),
            ]
        )
        for k, v in api.openapi_extra.items():
            if k not in self:
                self[k] = v

    def get_paths(self) -> DictStrAny:
        result: DictStrAny = {}
        for prefix, router in self.api._routers:
            for path, path_view in router.path_operations.items():
                full_path = "/".join([i for i in (prefix, path) if i])
                full_path = "/" + self.path_prefix + full_path
                full_path = normalize_path(full_path)
                full_path = re.sub(
                    r"{[^}:]+:", "{", full_path
                )  # remove path converters
                path_methods = self.methods(path_view.operations)
                if path_methods:
                    try:
                        result[full_path].update(path_methods)
                    except KeyError:
                        result[full_path] = path_methods

        return result

    def methods(self, operations: list) -> DictStrAny:
        result = {}
        for op in operations:
            if op.include_in_schema:
                operation_details = self.operation_details(op)
                for method in op.methods:
                    result[method.lower()] = operation_details
        return result

    def deep_dict_update(
        self, main_dict: Dict[Any, Any], update_dict: Dict[Any, Any]
    ) -> None:
        for key in update_dict:
            if (
                key in main_dict
                and isinstance(main_dict[key], dict)
                and isinstance(update_dict[key], dict)
            ):
                self.deep_dict_update(
                    main_dict[key], update_dict[key]
                )  # pragma: no cover
            else:
                main_dict[key] = update_dict[key]

    def operation_details(self, operation: Operation) -> DictStrAny:
        op_id = operation.operation_id or self.api.get_openapi_operation_id(operation)
        if op_id in self.all_operation_ids:
            print(
                bold_red_style(
                    f'Warning: operation_id "{op_id}" is already used (Try giving a different name to: {operation.view_func.__module__}.{operation.view_func.__name__})'
                )
            )
        self.all_operation_ids.add(op_id)
        result = {
            "operationId": op_id,
            "summary": operation.summary,
            "parameters": self.operation_parameters(operation),
            "responses": self.responses(operation),
        }

        if operation.description:
            result["description"] = operation.description

        if operation.tags:
            result["tags"] = operation.tags

        if operation.deprecated:
            result["deprecated"] = operation.deprecated  # type: ignore

        body = self.request_body(operation)
        if body:
            result["requestBody"] = body

        security = self.operation_security(operation)
        if security:
            result["security"] = security

        if operation.openapi_extra:
            self.deep_dict_update(result, operation.openapi_extra)

        return result

    def operation_parameters(self, operation: Operation) -> List[DictStrAny]:
        result = []
        for model in operation.models:
            if model.__ninja_param_source__ not in BODY_CONTENT_TYPES:
                result.extend(self._extract_parameters(model))
        return result

    def _extract_parameters(self, model: TModel) -> List[DictStrAny]:
        result = []

        schema = model.model_json_schema(
            ref_template=REF_TEMPLATE,
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
            for p_name, p_schema, p_required in flatten_properties(
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

    def _flatten_schema(self, model: TModel) -> DictStrAny:
        params = self._extract_parameters(model)
        flattened = {
            "title": model.__name__,  # type: ignore
            "type": "object",
            "properties": {p["name"]: p["schema"] for p in params},
        }
        required = [p["name"] for p in params if p["required"]]
        if required:
            flattened["required"] = required
        return flattened

    def _create_schema_from_model(
        self,
        model: TModel,
        by_alias: bool = True,
        remove_level: bool = True,
    ) -> Tuple[DictStrAny, bool]:
        if hasattr(model, "__ninja_flatten_map__"):
            schema = self._flatten_schema(model)
        else:
            schema = model.model_json_schema(
                ref_template=REF_TEMPLATE,
                by_alias=by_alias,
                schema_generator=NinjaGenerateJsonSchema,
            ).copy()

        # move Schemas from definitions
        if schema.get("$defs"):
            self.add_schema_definitions(schema.pop("$defs"))

        if remove_level and len(schema["properties"]) == 1:
            name, details = list(schema["properties"].items())[0]

            # ref = details["$ref"]
            required = name in schema.get("required", {})
            return details, required
        else:
            return schema, True

    def _create_multipart_schema_from_models(
        self, models: TModels
    ) -> Tuple[DictStrAny, str]:
        # We have File and Form or Body, so we need to use multipart (File)
        content_type = BODY_CONTENT_TYPES["file"]

        # get the various schemas
        result = merge_schemas(
            [
                self._create_schema_from_model(model, remove_level=False)[0]
                for model in models
            ]
        )
        result["title"] = "MultiPartBodyParams"

        return result, content_type

    def request_body(self, operation: Operation) -> DictStrAny:
        models = [
            m
            for m in operation.models
            if m.__ninja_param_source__ in BODY_CONTENT_TYPES
        ]
        if not models:
            return {}

        if len(models) == 1:
            model = models[0]
            content_type = BODY_CONTENT_TYPES[model.__ninja_param_source__]
            schema, required = self._create_schema_from_model(
                model, remove_level=model.__ninja_param_source__ == "body"
            )
        else:
            schema, content_type = self._create_multipart_schema_from_models(models)
            required = True

        return {
            "content": {content_type: {"schema": schema}},
            "required": required,
        }

    def responses(self, operation: Operation) -> Dict[int, DictStrAny]:
        assert bool(operation.response_models), f"{operation.response_models} empty"

        result = {}
        for status, model in operation.response_models.items():
            if status == Ellipsis:
                continue  # it's not yet clear what it means if user wants to output any other code

            description = responses.get(status, "Unknown Status Code")
            details: Dict[int, Any] = {status: {"description": description}}
            if model not in [None, NOT_SET]:
                # ::TODO:: test this: by_alias == True
                schema = self._create_schema_from_model(
                    model, by_alias=operation.by_alias
                )[0]
                details[status]["content"] = {
                    self.api.renderer.media_type: {"schema": schema}
                }
            result.update(details)

        return result

    def operation_security(self, operation: Operation) -> Optional[List[DictStrAny]]:
        if not operation.auth_callbacks:
            return None
        result = []
        for auth in operation.auth_callbacks:
            if hasattr(auth, "openapi_security_schema"):
                scopes: List[DictStrAny] = []  # TODO: scopes
                name = auth.__class__.__name__
                result.append({name: scopes})  # TODO: check if unique
                self.securitySchemes[name] = auth.openapi_security_schema
        return result

    def get_components(self) -> DictStrAny:
        result = {"schemas": self.schemas}
        if self.securitySchemes:
            result["securitySchemes"] = self.securitySchemes
        return result

    def add_schema_definitions(self, definitions: dict) -> None:
        # TODO: check if schema["definitions"] are unique
        # if not - workaround (maybe use pydantic.schema.schema(models)) to process list of models
        # assert set(definitions.keys()) - set(self.schemas.keys()) == set()
        # ::TODO:: this is broken in interesting ways for by_alias,
        #     because same schema (name) can have different values
        self.schemas.update(definitions)


def flatten_properties(
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
        else:
            for item in prop_details["allOf"]:
                yield from flatten_properties("", item, True, definitions)

    elif "items" in prop_details and "$ref" in prop_details["items"]:
        def_name = prop_details["items"]["$ref"].rsplit("/", 1)[-1]
        prop_details["items"].update(definitions[def_name])
        del prop_details["items"]["$ref"]  # seems num data is there so ref not needed
        yield prop_name, prop_details, prop_required

    elif "$ref" in prop_details:
        def_name = prop_details["$ref"].split("/")[-1]
        definition = definitions[def_name]
        yield from flatten_properties(prop_name, definition, prop_required, definitions)

    elif "properties" in prop_details:
        required = set(prop_details.get("required", []))
        for k, v in prop_details["properties"].items():
            is_required = k in required
            yield from flatten_properties(k, v, is_required, definitions)
    else:
        yield prop_name, prop_details, prop_required


def resolve_allOf(details: DictStrAny, definitions: DictStrAny) -> None:
    """
    resolves all $ref's in 'allOf' section
    """
    for item in details["allOf"]:
        if "$ref" in item:
            def_name = item["$ref"].rsplit("/", 1)[-1]
            item.update(definitions[def_name])
            del item["$ref"]


def merge_schemas(schemas: List[DictStrAny]) -> DictStrAny:
    result = schemas[0]
    for scm in schemas[1:]:
        result["properties"].update(scm["properties"])

    required_list = result.get("required", [])
    required_list.extend(
        itertools.chain.from_iterable(
            schema.get("required", ()) for schema in schemas[1:]
        )
    )
    if required_list:
        result["required"] = required_list
    return result
