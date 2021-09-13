import re
import warnings
from http.client import responses
from typing import TYPE_CHECKING, Any, Dict, Generator, List, Optional, Set, Tuple, Type

from pydantic import BaseModel
from pydantic.schema import model_schema as pydantic_model_schema

from ninja.constants import NOT_SET
from ninja.errors import ConfigError
from ninja.operation import Operation
from ninja.params_models import TModels
from ninja.types import DictStrAny
from ninja.utils import normalize_path

if TYPE_CHECKING:
    from ninja import NinjaAPI  # pragma: no cover

REF_PREFIX: str = "#/components/schemas/"

BODY_CONTENT_TYPES: Dict[str, str] = {
    "body": "application/json",
    "form": "application/x-www-form-urlencoded",
    "file": "multipart/form-data",
}


def model_schema(*args: Any, **kwargs: Any) -> Dict[str, Any]:
    """trap and report some errors in pydantic schema generation"""
    try:
        return pydantic_model_schema(*args, **kwargs)
    except KeyError as exc:
        from ninja.orm.factory import factory

        factory.check_for_duplicates_on_exception(exc)
        raise


def get_schema(api: "NinjaAPI", path_prefix: str = "") -> "OpenAPISchema":
    openapi = OpenAPISchema(api, path_prefix)
    return openapi


class OpenAPISchema(dict):
    def __init__(self, api: "NinjaAPI", path_prefix: str) -> None:
        self.api = api
        self.path_prefix = path_prefix
        self.schemas: DictStrAny = {}
        self.securitySchemes: DictStrAny = {}
        self.all_operation_ids: Set = set()
        super().__init__(
            [
                ("openapi", "3.0.2"),
                (
                    "info",
                    {
                        "title": api.title,
                        "version": api.version,
                        "description": api.description,
                    },
                ),
                ("paths", self.get_paths()),
                ("components", self.get_components()),
            ]
        )

    def get_paths(self) -> DictStrAny:
        result = {}
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

    def operation_details(self, operation: Operation) -> DictStrAny:
        op_id = operation.operation_id or self.api.get_openapi_operation_id(operation)
        if op_id in self.all_operation_ids:
            warnings.warn(
                f'operation_id "{op_id}" is already used (func: {operation.view_func})'
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
            result["deprecated"] = operation.deprecated

        body = self.request_body(operation)
        if body:
            result["requestBody"] = body

        security = self.operation_security(operation)
        if security:
            result["security"] = security

        return result

    def operation_parameters(self, operation: Operation) -> List[DictStrAny]:
        result = []
        for model in operation.models:
            if model._param_source in BODY_CONTENT_TYPES:
                continue

            schema = model_schema(model, ref_prefix=REF_PREFIX)

            required = set(schema.get("required", []))
            properties = schema["properties"]

            for name, details in properties.items():
                is_required = name in required
                p_name: str
                p_schema: DictStrAny
                p_required: bool
                for p_name, p_schema, p_required in flatten_properties(
                    name, details, is_required, schema.get("definitions", {})
                ):
                    param = {
                        "in": model._param_source,
                        "name": p_name,
                        "schema": p_schema,
                        "required": p_required,
                    }
                    result.append(param)

        return result

    def _create_schema_from_model(
        self,
        model: Type[BaseModel],
        by_alias: bool = False,
        remove_level: bool = True,
    ) -> Tuple[Any, bool]:
        schema = model_schema(model, ref_prefix=REF_PREFIX, by_alias=by_alias)

        # move Schemas from definitions
        if schema.get("definitions"):
            self.add_schema_definitions(schema.pop("definitions"))

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
        param_sources = {model._param_source for model in models}
        if "body" in param_sources:
            # ::TODO:: for now reject this.  This however, should be workable with multipart
            other = " & ".join(f"'{src.title()}'" for src in param_sources - {"body"})
            raise ConfigError(
                f"'Body' params currently incompatible with {other} params"
            )

        # for now, this should be the only possibility here.
        assert param_sources == {"form", "file"}

        # We have File and Form, so we need to use multipart (File)
        content_type = BODY_CONTENT_TYPES["file"]

        # merge the form and files schema
        schema, schema2 = tuple(
            self._create_schema_from_model(model, remove_level=False)[0]
            for model in models
        )

        schema["title"] = "FormFileParams"
        schema["properties"].update(schema2["properties"])
        required_list = schema.get("required", []) + schema2.get("required", [])
        if required_list:
            schema["required"] = required_list
        return schema, content_type

    def request_body(self, operation: Operation) -> DictStrAny:
        models = [m for m in operation.models if m._param_source in BODY_CONTENT_TYPES]
        if not models:
            return {}

        if len(models) == 1:
            model = models[0]
            content_type = BODY_CONTENT_TYPES[model._param_source]
            if model._param_source == "file":
                schema, required = self._create_schema_from_model(
                    model, remove_level=False
                )
            else:
                schema, required = self._create_schema_from_model(model)
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
                details[status]["content"] = {"application/json": {"schema": schema}}
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
                self.securitySchemes[name] = auth.openapi_security_schema  # type: ignore
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
    if "$ref" in prop_details:
        def_name = prop_details["$ref"].split("/")[-1]
        definition = definitions[def_name]
        if "properties" in definition:
            required = set(definition.get("required", []))
            for k, v in definition["properties"].items():
                is_required = k in required
                for p in flatten_properties(k, v, is_required, definitions):
                    yield p
        else:
            yield prop_name, definition, prop_required
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
