from http.client import responses
from typing import Any, Dict
from ninja.constants import NOT_SET
from ninja.operation import Operation


class ResponseBuilder:
    def build(self, operation: Operation, open_api_schema):
        assert bool(operation.response_models), f"{operation.response_models} empty"

        result = {}
        for status, model in operation.response_models.items():
            if status == Ellipsis:
                continue  # it's not yet clear what it means if user wants to output any other code

            description = responses.get(status, "Unknown Status Code")
            details: Dict[int, Any] = {status: {"description": description}}
            if model not in [None, NOT_SET]:
                # ::TODO:: test this: by_alias == True
                schema = open_api_schema.schema_builder._create_schema_from_model(
                    model, by_alias=operation.by_alias, mode="serialization"
                )[0]
                details[status]["content"] = {
                    open_api_schema.api.renderer.media_type: {"schema": schema}
                }
            result.update(details)

        return result