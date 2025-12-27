from typing import Any, Dict, List, Optional
from ninja.operation import Operation
from ninja.types import DictStrAny
from django.utils.termcolors import make_style

bold_red_style = make_style(opts=("bold",), fg="red")


class OperationDetailBuilder:
  def __init__(self, body_content_types):
      self.body_content_types = body_content_types

  def build(self, operation: Operation, open_api_schema) -> DictStrAny:
        op_id = operation.operation_id or open_api_schema.api.get_openapi_operation_id(operation)
        if op_id in open_api_schema.all_operation_ids:
            print(
                bold_red_style(
                    f'Warning: operation_id "{op_id}" is already used (Try giving a different name to: {operation.view_func.__module__}.{operation.view_func.__name__})'
                )
            )
        open_api_schema.all_operation_ids.add(op_id)
        result = {
            "operationId": op_id,
            "summary": operation.summary,
            "parameters": self.operation_parameters(operation, open_api_schema),
            "responses": open_api_schema.response_builder.build(operation, open_api_schema),
        }

        if operation.description:
            result["description"] = operation.description

        if operation.tags:
            result["tags"] = operation.tags

        if operation.deprecated:
            result["deprecated"] = operation.deprecated  # type: ignore

        body = open_api_schema.request_body_builder.request_body(operation, open_api_schema)
        if body:
            result["requestBody"] = body

        security = self.operation_security(operation, open_api_schema)
        if security:
            result["security"] = security

        if operation.openapi_extra:
            self.deep_dict_update(result, operation.openapi_extra)

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
                elif (
                    key in main_dict
                    and isinstance(main_dict[key], list)
                    and isinstance(update_dict[key], list)
                ):
                    main_dict[key].extend(update_dict[key])
                else:
                    main_dict[key] = update_dict[key]
    

  def operation_parameters(self, operation: Operation, open_api_schema) -> List[DictStrAny]:
        result = []
        for model in operation.models:
            if model.__ninja_param_source__ not in self.body_content_types:
                result.extend(open_api_schema.param_extractor._extract_parameters(model))
        return result
  
  def operation_security(self, operation: Operation, open_api_schema) -> Optional[List[DictStrAny]]:
        if not operation.auth_callbacks:
            return None
        result = []
        for auth in operation.auth_callbacks:
            if hasattr(auth, "openapi_security_schema"):
                scopes: List[DictStrAny] = []  # TODO: scopes
                name = auth.__class__.__name__
                result.append({name: scopes})  # TODO: check if unique
                open_api_schema.securitySchemes[name] = auth.openapi_security_schema
        return result