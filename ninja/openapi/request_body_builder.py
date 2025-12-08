import itertools
from typing import List, Tuple
from ninja.openapi.schema_builder import SchemaBuilder
from ninja.operation import Operation
from ninja.params.models import TModels
from ninja.types import DictStrAny


class RequestBodyBuilder:
    def __init__(self, body_content_types, ref_template):
        self.body_content_types = body_content_types
        self.ref_template = ref_template

    def request_body(self, operation: Operation, open_api_schema) -> DictStrAny:
        models = [
            m
            for m in operation.models
            if m.__ninja_param_source__ in self.body_content_types
        ]
        if not models:
            return {}

        if len(models) == 1:
            model = models[0]
            content_type = self.body_content_types[model.__ninja_param_source__]
            schema, required = open_api_schema.schema_builder._create_schema_from_model(
                model, remove_level=model.__ninja_param_source__ == "body"
            )
        else:
            schema, content_type = self._create_multipart_schema_from_models(models, open_api_schema)
            required = True

        return {
            "content": {content_type: {"schema": schema}},
            "required": required,
        }

    def _create_multipart_schema_from_models(
        self, models: TModels, open_api_schema
    ) -> Tuple[DictStrAny, str]:
        # We have File and Form or Body, so we need to use multipart (File)
        content_type = self.body_content_types["file"]

        # get the various schemas
        result = self.merge_schemas([
            open_api_schema.schema_builder._create_schema_from_model(model, remove_level=False)[0]
            for model in models
        ])
        result["title"] = "MultiPartBodyParams"

        return result, content_type

    def merge_schemas(self, schemas: List[DictStrAny]) -> DictStrAny:
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