import itertools
import re
from typing import TYPE_CHECKING, Generator, List, Set, Tuple

from django.utils.termcolors import make_style

from ninja.operation import Operation
from ninja.types import DictStrAny
from ninja.utils import normalize_path

if TYPE_CHECKING:
    from ninja import NinjaAPI  # pragma: no cover


def get_schema(api: "NinjaAPI", path_prefix: str = "") -> "OpenAPISchema":
    openapi = OpenAPISchema(api, path_prefix)
    return openapi


bold_red_style = make_style(opts=("bold",), fg="red")


class OpenAPISchema(dict):
    """
    OpenAPI schema document generator.

    This class is responsible for building the complete OpenAPI specification
    document. It delegates operation-specific schema computation to
    OperationSchemaBuilder instances, keeping this class focused on
    document orchestration.
    """

    def __init__(self, api: "NinjaAPI", path_prefix: str) -> None:
        self.api = api
        self.path_prefix = path_prefix
        self.schemas: DictStrAny = {}
        self.securitySchemes: DictStrAny = {}
        self.all_operation_ids: Set[str] = set()
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
        """Build the paths object containing all API endpoints."""
        result: DictStrAny = {}
        for prefix, router in self.api._routers:
            for path, path_view in router.path_operations.items():
                full_path = "/".join([i for i in (prefix, path) if i])
                full_path = "/" + self.path_prefix + full_path
                full_path = normalize_path(full_path)
                full_path = re.sub(
                    r"{[^}:]+:", "{", full_path
                )  # remove path converters
                path_methods = self._build_methods(path_view.operations)
                if path_methods:
                    try:
                        result[full_path].update(path_methods)
                    except KeyError:
                        result[full_path] = path_methods

        return result

    def _build_methods(self, operations: list) -> DictStrAny:
        """Build the methods object for a path from its operations."""
        result: DictStrAny = {}
        for op in operations:
            if op.include_in_schema:
                operation_details = self._build_operation(op)
                for method in op.methods:
                    result[method.lower()] = operation_details
        return result

    def _build_operation(self, operation: Operation) -> DictStrAny:
        """
        Build operation details using OperationSchemaBuilder.

        This method delegates to the builder pattern, keeping the
        OpenAPISchema class focused on document structure.
        """
        operation_builder_type = operation.get_operation_builder_type()
        builder = operation_builder_type(
            operation=operation,
            api=self.api,
        )
        result = builder.build()

        # Handle operation ID tracking and duplicate detection
        self._register_operation_id(result.operation_id, operation)

        # Merge collected schemas and security schemes
        self.add_schema_definitions(result.schemas)
        self.securitySchemes.update(result.security_schemes)

        return result.operation_details

    def _register_operation_id(self, op_id: str, operation: Operation) -> None:
        """Register an operation ID, warning if it's a duplicate."""
        if op_id in self.all_operation_ids:
            print(
                bold_red_style(
                    f'Warning: operation_id "{op_id}" is already used '
                    f"(Try giving a different name to: "
                    f"{operation.view_func.__module__}.{operation.view_func.__name__})"
                )
            )
        self.all_operation_ids.add(op_id)

    def get_components(self) -> DictStrAny:
        """Build the components object containing schemas and security schemes."""
        result: DictStrAny = {"schemas": self.schemas}
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
        else:  # pragma: no cover
            # TODO: this code was for pydanitc 1.7+ ... <2.9 - check if this is still needed
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
