from collections import OrderedDict

from ninja.utils import normalize_path
from pydantic.schema import model_schema

REF_PREFIX = "#/components/schemas/"


def get_schema(api: "NinjaAPI", path_prefix=""):
    openapi = OpenAPISchema(api, path_prefix)
    return openapi


class OpenAPISchema(OrderedDict):
    def __init__(self, api: "NinjaAPI", path_prefix: str):
        self.api = api
        self.path_prefix = path_prefix
        self.schemas = {}
        self.securitySchemes = {}
        super().__init__(
            [
                ("openapi", "3.0.2"),
                ("info", {"title": api.title, "version": api.version}),
                ("paths", self.get_paths()),
                ("components", self.get_components()),
            ]
        )

    def get_paths(self):
        result = {}
        for prefix, router in self.api._routers:
            for path, path_view in router.operations.items():
                full_path = "/".join([i for i in (prefix, path) if i])
                full_path = "/" + self.path_prefix + full_path
                full_path = normalize_path(full_path)
                result[full_path] = self.methods(path_view.operations)
        return result

    def methods(self, operations: list):
        result = {}
        for op in operations:
            for method in op.methods:
                result[method.lower()] = self.operation_details(op)
        return result

    def operation_details(self, operation):
        result = {
            # TODO: summary should be param of api.get(xxx, summary=yy)
            "summary": operation.view_func.__name__.title().replace("_", " "),
            "parameters": self.operation_parameters(operation),
            "responses": self.responses(operation),
        }

        body = self.request_body(operation)
        if body:
            result["requestBody"] = body

        security = self.operation_security(operation)
        if security:
            result["security"] = security

        return result

    def operation_parameters(self, operation):
        result = []
        for model in operation.models:
            if model._in == "body":
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

    def _create_schema_from_model(self, model):
        schema = model_schema(model, ref_prefix=REF_PREFIX)
        self.add_schema_definitions(schema["definitions"])
        name, details = list(schema["properties"].items())[0]

        # ref = details["$ref"]
        required = name in schema.get("required", {})
        return details, required

    def request_body(self, operation):
        # TODO: refactor
        models = [m for m in operation.models if m._in == "body"]
        if not models:
            return {}
        assert len(models) == 1

        schema, required = self._create_schema_from_model(models[0])

        return {
            "content": {"application/json": {"schema": schema}},
            "required": required,
        }

    def responses(self, operation):
        if operation.response_model:
            schema, _ = self._create_schema_from_model(operation.response_model)

            return {
                200: {
                    "description": "OK",
                    "content": {"application/json": {"schema": schema}},
                }
            }
        else:
            return {200: {"description": "OK"}}

    def operation_security(self, operation):
        if not operation.auth_callbacks:
            return
        result = []
        for auth in operation.auth_callbacks:
            if hasattr(auth, "openapi_security_schema"):
                scopes = []  # TODO: scopes
                name = auth.__class__.__name__
                result.append({name: scopes})  # TODO: check if unique
                self.securitySchemes[name] = auth.openapi_security_schema
        return result

    def get_components(self):
        result = {"schemas": self.schemas}
        if self.securitySchemes:
            result["securitySchemes"] = self.securitySchemes
        return result

    def add_schema_definitions(self, definitions: dict):
        # TODO: check if schema["definitions"] are unique
        # if not - workaround (maybe use pydantic.schema.schema(models)) to process list of models
        self.schemas.update(definitions)
