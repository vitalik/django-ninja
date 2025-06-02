import json
from typing import Any, Mapping, Optional, Type

from django.http import HttpRequest
from ninja.responses import *

__all__ = ["BaseRenderer", "JSONRenderer", "Message_JSONRenderer"]

class BaseRenderer:
    """
    Abstract base class for defining custom renderers in a Ninja API.

    Attributes:
        media_type (Optional[str]): MIME type of the response, e.g., "application/json".
        charset (str): Character encoding for the response, default is "utf-8".
    """

    media_type: Optional[str] = None
    charset: str = "utf-8"

    def render(self, request: HttpRequest, data: Any, *, response_status: int) -> Any:
        """
        Render the response content. This method must be overridden in subclasses.

        Args:
            request (HttpRequest): The incoming Django HTTP request.
            data (Any): The data to be rendered into the response body.
            response_status (int): The HTTP status code for the response.

        Returns:
            Any: The rendered content.

        Raises:
            NotImplementedError: If the method is not overridden by a subclass.
        """
        raise NotImplementedError("Please implement .render() method")


class JSONRenderer(BaseRenderer):
    """
    A basic JSON renderer using Django Ninja's JSON encoder.

    Attributes:
        media_type (str): MIME type set to "application/json".
        encoder_class (Type[json.JSONEncoder]): JSON encoder class to serialize data.
        json_dumps_params (Mapping[str, Any]): Additional parameters for `json.dumps`.
    """

    media_type = "application/json"
    encoder_class: Type[json.JSONEncoder] = NinjaJSONEncoder
    json_dumps_params: Mapping[str, Any] = {}

    def render(self, request: HttpRequest, data: Any, *, response_status: int) -> Any:
        """
        Renders the data into a JSON-formatted string.

        Args:
            request (HttpRequest): The incoming request (unused here).
            data (Any): The data to be serialized.
            response_status (int): The HTTP status code (unused here).

        Returns:
            str: A JSON string representation of the data.
        """
        return json.dumps(data, cls=self.encoder_class, **self.json_dumps_params)


class Message_JSONRenderer(BaseRenderer):
    """
    A JSON renderer that wraps the response with additional metadata including
    status code and a corresponding human-readable message.

    Attributes:
        media_type (str): MIME type set to "application/json".
        encoder_class (Type[json.JSONEncoder]): JSON encoder class to serialize data.
        json_dumps_params (Mapping[str, Any]): Additional parameters for `json.dumps`.
    """

    media_type = "application/json"
    encoder_class: Type[json.JSONEncoder] = NinjaJSONEncoder
    json_dumps_params: Mapping[str, Any] = {}

    def render(
        self, request: HttpRequest, data: Any, *, response_status: int
    ) -> Any:
        """
        Renders the data into a structured JSON response with status and message.

        Args:
            request (HttpRequest): The incoming request (unused here).
            data (Any): The data to be serialized.
            response_status (int): The HTTP status code.

        Returns:
            str: A JSON string with structure: {status, message, data}.
        """
        info_message = response_status in codes_1xx
        success = response_status in codes_2xx
        redirect_message = response_status in codes_3xx
        client_error = response_status in codes_4xx
        server_error = response_status in codes_5xx

        # Determine message based on status code class
        if success:
            message = "Success"
        elif client_error:
            message = "Client Error"
        elif server_error:
            message = "Server Error"
        elif redirect_message:
            message = "Redirect"
        elif info_message:
            message = "Informational"
        else:
            message = "Unknown Status"

        # Wrap original data with status and message
        response_data = {
            "status": response_status,
            "message": message,
            "data": data,
        }

        return json.dumps(
            response_data, cls=self.encoder_class, **self.json_dumps_params
        )
