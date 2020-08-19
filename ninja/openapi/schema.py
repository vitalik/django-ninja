from collections import OrderedDict
from pydantic.schema import model_schema
from ninja.utils import normalize_path

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
            "requestBody": self.request_body(operation),
            "responses": self.responses(operation),
            "security": self.operation_security(operation),
        }

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
                    # This is a specail case when we group multiple path or query arguemtns into single schema
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

    def request_body(self, operation):
        # TODO: refactor
        models = [m for m in operation.models if m._in == "body"]
        if not models:
            return {}
        assert len(models) == 1
        schema = model_schema(models[0], ref_prefix=REF_PREFIX)

        self.add_schema_definitions(schema["definitions"])

        properties = list(
            [(k, v) for k, v in schema["properties"].items()]
        )  # TODO: can be just list(schema["properties"].items()) ?
        assert len(properties) == 1

        name, details = properties[0]
        ref = details["$ref"]

        return {
            "content": {"application/json": {"schema": {"$ref": ref}}},
            "required": name in schema.get("required", {}),
        }

    def operation_security(self, operation):
        if not operation.auth:
            return
        result = []
        for auth in operation.auth:
            if hasattr(auth, "openapi_securty_schema"):
                scopes = []  # TODO: scopes
                name = auth.__class__.__name__
                result.append({name: scopes})  # TODO: check if unique
                self.securitySchemes[name] = auth.openapi_securty_schema
        return result

    def responses(self, operation):
        return {200: {"description": "OK"}}

    def get_components(self):
        result = {"schemas": self.schemas}
        if self.securitySchemes:
            result["securitySchemes"] = self.securitySchemes
        return result

    def add_schema_definitions(self, definitions: dict):
        # TODO: check if schema["definitions"] are unique
        # if not - workarond (maybe use pydantic.schema.schema(models)) to process list of models
        self.schemas.update(definitions)
