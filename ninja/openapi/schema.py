import warnings
from typing import TYPE_CHECKING, Any, Dict, List, Optional, Set, Tuple, Type

from pydantic import BaseModel
from pydantic.schema import model_schema

from ninja.constants import NOT_SET
from ninja.operation import Operation
from ninja.types import DictStrAny
from ninja.utils import normalize_path

if TYPE_CHECKING:
    from ninja import NinjaAPI  # pragma: no cover

REF_PREFIX: str = "#/components/schemas/"

BODY_PARAMS: Set[str] = {"body", "form", "file"}


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
                path_methods = self.methods(path_view.operations)
                if path_methods:
                    result[full_path] = path_methods
        return result

    def methods(self, operations: list) -> DictStrAny:
        result = {}
        for op in operations:
            if not op.include_in_schema:
                continue
            for method in op.methods:
                result[method.lower()] = self.operation_details(op)
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
            if model._in in BODY_PARAMS:
                continue

            schema = model_schema(model, ref_prefix=REF_PREFIX)

            num_properties = len(schema["properties"])
            if num_properties == 1 and "definitions" in schema:
                prop_definition = list(schema["definitions"].values())[0]
                if prop_definition["type"] == "object":
                    # This is a specail case when we group multiple path or query arguments into single schema
                    # https://django-ninja.rest-framework.com/tutorial/path-params/#using-schema
                    schema = prop_definition
                else:
                    # resolving $refs (seems only for enum) # TODO: better keep that ref in components/schemas/
                    prop_name = list(schema["properties"].keys())[0]
                    schema["properties"][prop_name] = prop_definition

            required = set(schema.get("required", []))

            for name, details in schema["properties"].items():
                param = {"in": model._in, "name": name, "required": name in required}
                param["schema"] = details
                result.append(param)
        return result

    def _create_schema_from_model(
        self, model: Type[BaseModel], by_alias: bool = True
    ) -> Tuple[Any, bool]:
        schema = model_schema(model, ref_prefix=REF_PREFIX, by_alias=by_alias)
        if schema.get("definitions"):
            self.add_schema_definitions(schema["definitions"])
        name, details = list(schema["properties"].items())[0]

        # ref = details["$ref"]
        required = name in schema.get("required", {})
        return details, required

    def request_body(self, operation: Operation) -> DictStrAny:
        # TODO: refactor
        models = [m for m in operation.models if m._in in BODY_PARAMS]
        if not models:
            return {}
        assert len(models) == 1

        model = models[0]
        content_type = self.get_body_content_type(model)

        if model._in == "body":
            schema, required = self._create_schema_from_model(model)
        else:
            assert model._in in ("form", "file")
            schema = model_schema(model, ref_prefix=REF_PREFIX)
            required = True

        return {
            "content": {content_type: {"schema": schema}},
            "required": required,
        }

    def get_body_content_type(self, model: Any) -> str:
        types = {
            "body": "application/json",
            "form": "application/x-www-form-urlencoded",
            "file": "multipart/form-data",
        }
        return types[model._in]

    def responses(self, operation: Operation) -> Dict[int, DictStrAny]:
        assert bool(operation.response_models), f"{operation.response_models} empty"

        result = {}
        for status, model in operation.response_models.items():

            if status == Ellipsis:
                continue  # it's not yet clear what it means if user want's to output any other code

            description = status < 300 and "OK" or "Error"
            details: Dict[int, Any] = {status: {"description": description}}
            if model not in [None, NOT_SET]:
                schema, _ = self._create_schema_from_model(model, by_alias=False)
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
        self.schemas.update(definitions)
