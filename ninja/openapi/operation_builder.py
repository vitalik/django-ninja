"""
Builder pattern implementation for OpenAPI operation schema generation.

This module provides the OperationSchemaBuilder class which encapsulates
all schema computation logic for a single Operation, separating it from
the overall OpenAPI document generation.
"""

from dataclasses import dataclass, field
from http.client import responses
from typing import TYPE_CHECKING, Any, Dict, List, Optional, Tuple

from pydantic.json_schema import JsonSchemaMode

from ninja.constants import NOT_SET
from ninja.params.models import TModel, TModels
from ninja.schema import NinjaGenerateJsonSchema
from ninja.types import DictStrAny

if TYPE_CHECKING:
    from ninja import NinjaAPI
    from ninja.operation import Operation

REF_TEMPLATE: str = "#/components/schemas/{model}"

BODY_CONTENT_TYPES: Dict[str, str] = {
    "body": "application/json",
    "form": "application/x-www-form-urlencoded",
    "file": "multipart/form-data",
}


@dataclass
class OperationSchemaResult:
    """
    Result of building an operation schema.

    This dataclass contains all the computed schema components that
    OpenAPISchema needs to integrate into the final document.
    """

    operation_id: str
    """The unique operation identifier."""

    operation_details: DictStrAny
    """The complete operation details dictionary for the OpenAPI spec."""

    schemas: DictStrAny = field(default_factory=dict)
    """Schema definitions ($defs) to be added to components/schemas."""

    security_schemes: DictStrAny = field(default_factory=dict)
    """Security schemes to be added to components/securitySchemes."""


class OperationSchemaBuilder:
    """
    Builder for computing OpenAPI schema components for a single Operation.

    This class encapsulates all the logic for generating OpenAPI schema
    elements from an Operation object, including:
    - Operation details (operationId, summary, description, tags, etc.)
    - Parameters (path, query, header, cookie)
    - Request body schemas
    - Response schemas
    - Security requirements

    The builder returns an OperationSchemaResult containing all computed
    schemas and metadata, which the caller (OpenAPISchema) uses to update
    its document state.

    Usage:
        builder = OperationSchemaBuilder(operation=op, api=api)
        result = builder.build()
    """

    def __init__(
        self,
        operation: "Operation",
        api: "NinjaAPI",
    ) -> None:
        """
        Initialize the OperationSchemaBuilder.

        Args:
            operation: The Operation object to build schema for.
            api: The NinjaAPI instance (needed for operation_id generation and renderer).
        """
        self.operation = operation
        self.api = api
        # Internal collectors - will be returned in result
        self._schemas: DictStrAny = {}
        self._security_schemes: DictStrAny = {}

    def build(self) -> OperationSchemaResult:
        """
        Build the complete operation schema result.

        Returns:
            OperationSchemaResult containing operation_id, operation_details,
            schemas to add, and security_schemes to add.
        """
        op_id = self._get_operation_id()
        operation_details: DictStrAny = {
            "operationId": op_id,
            "summary": self.operation.summary,
            "parameters": self.build_parameters(),
            "responses": self.build_responses(),
        }

        if self.operation.description:
            operation_details["description"] = self.operation.description

        if self.operation.tags:
            operation_details["tags"] = self.operation.tags

        if self.operation.deprecated:
            operation_details["deprecated"] = self.operation.deprecated

        body = self.build_request_body()
        if body:
            operation_details["requestBody"] = body

        security = self.build_security()
        if security:
            operation_details["security"] = security

        if self.operation.openapi_extra:
            self._deep_dict_update(operation_details, self.operation.openapi_extra)

        return OperationSchemaResult(
            operation_id=op_id,
            operation_details=operation_details,
            schemas=self._schemas,
            security_schemes=self._security_schemes,
        )

    def _get_operation_id(self) -> str:
        """Get or generate the operation ID."""
        return self.operation.operation_id or self.api.get_openapi_operation_id(
            self.operation
        )

    def build_parameters(self) -> List[DictStrAny]:
        """
        Build the parameters list for the operation.

        Returns:
            A list of parameter dictionaries for path, query, header, and cookie params.
        """
        result: List[DictStrAny] = []
        for model in self.operation.models:
            if model.__ninja_param_source__ not in BODY_CONTENT_TYPES:
                result.extend(self._extract_parameters(model))
        return result

    def _extract_parameters(self, model: TModel) -> List[DictStrAny]:
        """Extract parameters from a model's JSON schema."""
        from ninja.openapi.schema import flatten_properties

        result: List[DictStrAny] = []

        schema = model.model_json_schema(
            ref_template=REF_TEMPLATE,
            schema_generator=NinjaGenerateJsonSchema,
        )

        required = set(schema.get("required", []))
        properties = schema["properties"]

        if "$defs" in schema:
            self._collect_schema_definitions(schema["$defs"])

        for name, details in properties.items():
            is_required = name in required
            for p_name, p_schema, p_required in flatten_properties(
                name, details, is_required, schema.get("$defs", {})
            ):
                if not p_schema.get("include_in_schema", True):
                    continue

                param: DictStrAny = {
                    "in": model.__ninja_param_source__,
                    "name": p_name,
                    "schema": p_schema,
                    "required": p_required,
                }

                # Copy description from schema to param
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

    def build_request_body(self) -> DictStrAny:
        """
        Build the request body schema for the operation.

        Returns:
            A dictionary containing the request body schema, or empty dict if no body.
        """
        models = [
            m
            for m in self.operation.models
            if m.__ninja_param_source__ in BODY_CONTENT_TYPES
        ]
        if not models:
            return {}

        if len(models) == 1:
            model = models[0]
            content_type = BODY_CONTENT_TYPES[model.__ninja_param_source__]
            schema, required = self._create_schema_from_model(
                model,
                remove_level=model.__ninja_param_source__ == "body",
                mode="validation",
            )
        else:
            schema, content_type = self._create_multipart_schema_from_models(
                models, mode="validation"
            )
            required = True

        return {
            "content": {content_type: {"schema": schema}},
            "required": required,
        }

    def build_responses(self) -> Dict[int, DictStrAny]:
        """
        Build the responses dictionary for the operation.

        Returns:
            A dictionary mapping status codes to response schemas.
        """
        assert bool(
            self.operation.response_models
        ), f"{self.operation.response_models} empty"

        result: Dict[int, DictStrAny] = {}
        for status, model in self.operation.response_models.items():
            if status == Ellipsis:
                continue  # Not clear what it means if user wants to output any other code

            description = responses.get(status, "Unknown Status Code")
            details: Dict[int, Any] = {status: {"description": description}}
            if model not in [None, NOT_SET]:
                schema = self._create_schema_from_model(
                    model, by_alias=self.operation.by_alias, mode="serialization"
                )[0]
                details[status]["content"] = {
                    self.api.renderer.media_type: {"schema": schema}
                }
            result.update(details)

        return result

    def build_security(self) -> Optional[List[DictStrAny]]:
        """
        Build the security requirements for the operation.

        Returns:
            A list of security requirement objects, or None if no auth.
        """
        if not self.operation.auth_callbacks:
            return None

        result: List[DictStrAny] = []
        for auth in self.operation.auth_callbacks:
            if hasattr(auth, "openapi_security_schema"):
                scopes: List[DictStrAny] = []  # TODO: scopes
                name = auth.__class__.__name__
                result.append({name: scopes})
                self._security_schemes[name] = auth.openapi_security_schema
        return result

    def _create_schema_from_model(
        self,
        model: TModel,
        by_alias: bool = True,
        remove_level: bool = True,
        mode: JsonSchemaMode = "validation",
    ) -> Tuple[DictStrAny, bool]:
        """Create a JSON schema from a pydantic model."""
        if hasattr(model, "__ninja_flatten_map__"):
            schema = self._flatten_schema(model)
        else:
            schema = model.model_json_schema(
                ref_template=REF_TEMPLATE,
                by_alias=by_alias,
                schema_generator=NinjaGenerateJsonSchema,
                mode=mode,
            ).copy()

        # Collect schemas from definitions
        if schema.get("$defs"):
            self._collect_schema_definitions(schema.pop("$defs"))

        if remove_level and len(schema["properties"]) == 1:
            name, details = list(schema["properties"].items())[0]
            required = name in schema.get("required", {})
            return details, required
        else:
            return schema, True

    def _flatten_schema(self, model: TModel) -> DictStrAny:
        """Flatten a model's schema for query/path parameters."""
        params = self._extract_parameters(model)
        flattened: DictStrAny = {
            "title": model.__name__,  # type: ignore
            "type": "object",
            "properties": {p["name"]: p["schema"] for p in params},
        }
        required = [p["name"] for p in params if p["required"]]
        if required:
            flattened["required"] = required
        return flattened

    def _create_multipart_schema_from_models(
        self,
        models: TModels,
        mode: JsonSchemaMode = "validation",
    ) -> Tuple[DictStrAny, str]:
        """Create a multipart schema from multiple models (File + Form)."""
        from ninja.openapi.schema import merge_schemas

        content_type = BODY_CONTENT_TYPES["file"]

        result = merge_schemas([
            self._create_schema_from_model(model, remove_level=False, mode=mode)[0]
            for model in models
        ])
        result["title"] = "MultiPartBodyParams"

        return result, content_type

    def _collect_schema_definitions(self, definitions: dict) -> None:
        """Collect schema definitions to be returned in the result."""
        self._schemas.update(definitions)

    def _deep_dict_update(
        self, main_dict: Dict[Any, Any], update_dict: Dict[Any, Any]
    ) -> None:
        """Recursively update a dictionary, merging nested dicts and extending lists."""
        for key in update_dict:
            if (
                key in main_dict
                and isinstance(main_dict[key], dict)
                and isinstance(update_dict[key], dict)
            ):
                self._deep_dict_update(main_dict[key], update_dict[key])
            elif (
                key in main_dict
                and isinstance(main_dict[key], list)
                and isinstance(update_dict[key], list)
            ):
                main_dict[key].extend(update_dict[key])
            else:
                main_dict[key] = update_dict[key]
