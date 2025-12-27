import re
from typing import TYPE_CHECKING, Dict, Set


from ninja.openapi.operation_details_builder import OperationDetailBuilder
from ninja.openapi.param_extractor import ParameterExtractor
from ninja.openapi.request_body_builder import RequestBodyBuilder
from ninja.openapi.response_builder import ResponseBuilder
from ninja.openapi.schema_builder import SchemaBuilder
from ninja.params.models import TModel
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

class OpenAPISchema(dict):
    def __init__(self, api: "NinjaAPI", path_prefix: str) -> None:
        self.api = api
        self.path_prefix = path_prefix
        self.schemas: DictStrAny = {}
        self.securitySchemes: DictStrAny = {}
        self.all_operation_ids: Set = set()
        self.schema_builder = SchemaBuilder(REF_TEMPLATE, self)
        self.param_extractor = ParameterExtractor(REF_TEMPLATE, self)
        self.request_body_builder = RequestBodyBuilder(BODY_CONTENT_TYPES, REF_TEMPLATE)
        self.response_builder = ResponseBuilder()
        self.operation_details_builder = OperationDetailBuilder(BODY_CONTENT_TYPES)

        extra_info = api.openapi_extra.get("info", {})
        super().__init__([
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
        ])
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
                operation_details = self.operation_details_builder.build(op, self)
                for method in op.methods:
                    result[method.lower()] = operation_details
        return result

    def get_components(self) -> DictStrAny:
        result = {"schemas": self.schemas}
        if self.securitySchemes:
            result["securitySchemes"] = self.securitySchemes
        return result
    
    def add_schema_definitions(self, definitions: dict) -> None:
        self.schemas.update(definitions)

def resolve_allOf(details: DictStrAny, definitions: DictStrAny) -> None:
    """
    resolves all $ref's in 'allOf' section
    """
    for item in details["allOf"]:
        if "$ref" in item:
            def_name = item["$ref"].rsplit("/", 1)[-1]
            item.update(definitions[def_name])
            del item["$ref"]