"""
This module contains enumerations for standard HTTP and WebSocket status codes, defined according to IETF RFCs. 
These enums make it easier to handle and reference HTTP and WebSocket status codes in a structured way.

The `HTTPStatus` Enum represents all HTTP status codes from RFC 7231 and RFC 7540, categorizing them into informational, success, redirection, client error, and server error responses. 
It also includes HTTP/2 status codes as per RFC 7540.

The `WebSocketStatus` Enum represents WebSocket close status codes from RFC 6455, including common closure reasons and reserved codes.

References:
- RFC 7231 (HTTP/1): https://tools.ietf.org/html/rfc7231
- RFC 7540 (HTTP/2): https://tools.ietf.org/html/rfc7540
- RFC 6455 (WebSocket): https://tools.ietf.org/html/rfc6455

Django Ninja:
This module can be used in conjunction with Django Ninja, a modern web framework for building APIs with Python 3.6+ based on standard Python type hints and Pydantic models. By using this module, you can easily reference standard HTTP and WebSocket status codes in your API responses and request validations.

In Django Ninja, these status codes can be incorporated in:
1. Response models, where you can define the HTTP status code for various API endpoints.
2. Pydantic schemas, for validating data and handling responses with proper status codes.
3. WebSocket handling, to indicate closure reasons via WebSocket status codes.

Example usage:

-  Single Response Example (HTTPStatus): 
    This example demonstrates how to use the `HTTPStatus` enum in a Django Ninja API view to return different HTTP status codes based on conditions.

    ```python
    from ninja import Router, status
    # or
    from ninja.status import HTTPStatus  # Importing the HTTPStatus Enum for HTTP status codes

    router = Router()

    @router.get("/status")
    def check_status(request):
        # Simulate a condition for demonstration
        condition = "success"  # You can change this to "error" or "not_found" to test other cases

        if condition == "success":
            return {"message": "Request was successful!"}, HTTPStatus.HTTP_OK  # HTTP 200 OK
        elif condition == "not_found":
            return {"message": "Resource not found!"}, HTTPStatus.HTTP_NOT_FOUND  # HTTP 404 Not Found
        else:
            return {"message": "Bad request!"}, HTTPStatus.HTTP_BAD_REQUEST  # HTTP 400 Bad Request
    ```

- Multiple Response Example (HTTPStatus):
    This example shows how to define multiple possible responses for different HTTP status codes, using `HTTPStatus` in a Django Ninja API view.

    ```python
    from ninja import Router, status
    # or
    from ninja.status import HTTPStatus  # Importing the HTTPStatus Enum for HTTP status codes

    router = Router()

    # Define response schemas for different outcomes
    class SuccessResponse(Schema):
        message: str
        data: dict

    class ErrorResponse(Schema):
        detail: str

    class NotFoundResponse(Schema):
        detail: str
        resolution: str

    @router.get(
        "/example", 
        response={
            HTTPStatus.HTTP_OK: SuccessResponse, 
            HTTPStatus.HTTP_NOT_FOUND: NotFoundResponse, 
            HTTPStatus.HTTP_BAD_REQUEST: ErrorResponse
        }
    )
    def example_view(request):
        # Simulate success, error, or not found based on some condition
        condition = "not_found"  # You can change this to test different conditions
        
        if condition == "success":
            return {
                "message": "Request successful", 
                "data": {"key": "value"}
                }, HTTPStatus.HTTP_OK
        elif condition == "not_found":
            return {
                "detail": "Resource not found", 
                "resolution": "Check the URL or try again later"
                }, HTTPStatus.HTTP_NOT_FOUND
        else:
            return {
                "detail": "Bad request. Invalid input."
                }, HTTPStatus.HTTP_BAD_REQUEST
    ```

- WebSocketStatus Example:
    This example demonstrates how to use the `WebSocketStatus` enum to manage WebSocket closure status codes.

    ```python
    from ninja import Router, WebSocketStatus
    # or
    from ninja.status import WebSocketStatus  # Importing the HTTPStatus Enum for HTTP status codes

    router = Router()

    @router.websocket("/ws")
    async def websocket_endpoint(websocket):
        await websocket.accept()  # Accept the WebSocket connection
        try:
            # Simulate handling the WebSocket connection
            await websocket.send_text("Hello, WebSocket!")  # Send a message to the client
            # Simulate closure condition
            await websocket.close(code=WebSocketStatus.NORMAL_CLOSURE)  # Close the connection with status code 1000
        except Exception as e:
            # Handle errors and close the WebSocket with an error status code
            await websocket.send_text(f"Error: {str(e)}")
            await websocket.close(code=WebSocketStatus.INTERNAL_ERROR)  # Close with error code 1011
    ```

    Explanation:
    - The WebSocket connection is accepted, and a message is sent to the client.
    - After that, the connection is closed with a normal closure status code (`1000`), indicating a successful closure.
    - If any error occurs during the connection handling, the WebSocket is closed with an internal error status code (`1011`).

---
"""


from __future__ import annotations
from enum import Enum

class HTTPStatus(Enum):
    """
    Enum for HTTP Status Codes as defined by RFC 7231 and RFC 7540 for HTTP/1.x and HTTP/2.

    This Enum class represents the official HTTP status codes for HTTP/1.x (RFC 7231) and HTTP/2 (RFC 7540).
    The status codes are categorized into five groups:
    1. Informational responses (100–199)
    2. Successful responses (200–299)
    3. Redirection responses (300–399)
    4. Client error responses (400–499)
    5. Server error responses (500–599)

    For further reference on HTTP status codes, see:
    - RFC 7231: https://tools.ietf.org/html/rfc7231
    - RFC 7540: https://tools.ietf.org/html/rfc7540

    Attributes:
        HTTP_CONTINUE: 100 - The client should continue with its request.
        HTTP_SWITCHING_PROTOCOLS: 101 - The server is switching protocols as requested by the client.
        HTTP_OK: 200 - The request was successful.
        HTTP_CREATED: 201 - The request has been fulfilled and resulted in the creation of a new resource.
        HTTP_ACCEPTED: 202 - The request has been accepted but not yet acted upon.
        HTTP_BAD_REQUEST: 400 - The server cannot process the request due to a client error.
        HTTP_NOT_FOUND: 404 - The requested resource could not be found.
        HTTP_INTERNAL_SERVER_ERROR: 500 - The server encountered an unexpected condition that prevented it from fulfilling the request.

    Example:
        HTTPStatus.HTTP_OK  # Returns the HTTP status code 200
    """
    
    # Informational responses (100–199)
    HTTP_CONTINUE                           = 100
    HTTP_SWITCHING_PROTOCOLS                = 101
    HTTP_PROCESSING                         = 102
    HTTP_EARLY_HINTS                        = 103

    # Successful responses (200–299)
    HTTP_OK                                 = 200
    HTTP_CREATED                            = 201
    HTTP_ACCEPTED                           = 202
    HTTP_NON_AUTHORITATIVE_INFORMATION      = 203
    HTTP_NO_CONTENT                         = 204
    HTTP_RESET_CONTENT                      = 205
    HTTP_PARTIAL_CONTENT                    = 206
    HTTP_MULTI_STATUS                       = 207  
    HTTP_ALREADY_REPORTED                   = 208 
    HTTP_IM_USED                            = 226 

    # Redirection responses (300–399)
    HTTP_MULTIPLE_CHOICES                   = 300
    HTTP_MOVED_PERMANENTLY                  = 301
    HTTP_FOUND                              = 302
    HTTP_SEE_OTHER                          = 303
    HTTP_NOT_MODIFIED                       = 304
    HTTP_USE_PROXY                          = 305  
    HTTP_TEMPORARY_REDIRECT                 = 307
    HTTP_PERMANENT_REDIRECT                 = 308

    # Client error responses (400–499)
    HTTP_BAD_REQUEST                        = 400
    HTTP_UNAUTHORIZED                       = 401
    HTTP_PAYMENT_REQUIRED                   = 402
    HTTP_FORBIDDEN                          = 403
    HTTP_NOT_FOUND                          = 404
    HTTP_METHOD_NOT_ALLOWED                 = 405
    HTTP_NOT_ACCEPTABLE                     = 406
    HTTP_PROXY_AUTHENTICATION_REQUIRED      = 407
    HTTP_REQUEST_TIMEOUT                    = 408
    HTTP_CONFLICT                           = 409
    HTTP_GONE                               = 410
    HTTP_LENGTH_REQUIRED                    = 411
    HTTP_PRECONDITION_FAILED                = 412
    HTTP_PAYLOAD_TOO_LARGE                  = 413
    HTTP_URI_TOO_LONG                       = 414
    HTTP_UNSUPPORTED_MEDIA_TYPE             = 415
    HTTP_RANGE_NOT_SATISFIABLE              = 416
    HTTP_EXPECTATION_FAILED                 = 417
    HTTP_I_AM_A_TEAPOT                      = 418  
    HTTP_MISDIRECTED_REQUEST                = 421
    HTTP_UNPROCESSABLE_ENTITY               = 422  
    HTTP_LOCKED                             = 423  
    HTTP_FAILED_DEPENDENCY                  = 424  
    HTTP_TOO_EARLY                          = 425
    HTTP_UPGRADE_REQUIRED                   = 426
    HTTP_PRECONDITION_REQUIRED              = 428
    HTTP_TOO_MANY_REQUESTS                  = 429
    HTTP_REQUEST_HEADER_FIELDS_TOO_LARGE    = 431
    HTTP_UNAVAILABLE_FOR_LEGAL_REASONS      = 451

    # Server error responses (500–599)
    HTTP_INTERNAL_SERVER_ERROR              = 500
    HTTP_NOT_IMPLEMENTED                    = 501
    HTTP_BAD_GATEWAY                        = 502
    HTTP_SERVICE_UNAVAILABLE                = 503
    HTTP_GATEWAY_TIMEOUT                    = 504
    HTTP_VERSION_NOT_SUPPORTED              = 505
    HTTP_VARIANT_ALSO_NEGOTIATES            = 506
    HTTP_INSUFFICIENT_STORAGE               = 507  
    HTTP_LOOP_DETECTED                      = 508 
    HTTP_NOT_EXTENDED                       = 510
    HTTP_NETWORK_AUTHENTICATION_REQUIRED    = 511

    # HTTP/2 Status Codes (RFC 7540)
    HTTP_NO_ERROR                           = 0
    HTTP_PROTOCOL_ERROR                     = 1
    HTTP_INTERNAL_ERROR                     = 2
    HTTP_FLOW_CONTROL_ERROR                 = 3
    HTTP_SETTINGS_TIMEOUT                   = 4
    HTTP_STREAM_CLOSED                      = 5
    HTTP_STREAM_ERROR                       = 6
    HTTP_MALFORMED_FRAME                    = 7
    HTTP_ENHANCE_YOUR_CALM                  = 8
    HTTP_INADEQUATE_SECURITY                = 9
    HTTP_HTTP_1_1_REQUIRED                  = 10


class WebSocketStatus(Enum):
    """
    Enum for WebSocket Closure Status Codes as defined in RFC 6455.

    This Enum class represents the WebSocket closure status codes (1000–1015) as defined in the WebSocket protocol (RFC 6455).
    These codes indicate why a WebSocket connection was closed, ranging from normal closure to protocol errors or unexpected conditions.
    
    Each status code corresponds to a specific reason for the WebSocket connection being closed. For example:
    - `1000` indicates a successful closure.
    - `1006` indicates an abnormal closure due to no close frame being received.
    - `1008` represents a policy violation by the client.

    For further reference on WebSocket closure status codes, see:
    - RFC 6455: https://tools.ietf.org/html/rfc6455

    Attributes:
        NORMAL_CLOSURE: 1000 - Normal closure, the connection successfully closed.
        GOING_AWAY: 1001 - The server is going away, e.g., restarting.
        PROTOCOL_ERROR: 1002 - The server encountered a protocol error.
        UNSUPPORTED_DATA: 1003 - The server cannot handle the data type.
        NO_STATUS_RECEIVED: 1005 - No status code was received.
        ABNORMAL_CLOSURE: 1006 - Abnormal closure, no close frame was received.
        INTERNAL_ERROR: 1011 - The server encountered an internal error.

    Example:
        WebSocketStatus.NORMAL_CLOSURE  # Returns the WebSocket closure code 1000
    """

    
    # WebSocket Closure Status Codes (1000-1100)
    NORMAL_CLOSURE                          = 1000
    GOING_AWAY                              = 1001
    PROTOCOL_ERROR                          = 1002
    UNSUPPORTED_DATA                        = 1003
    RESERVED                                = 1004
    NO_STATUS_RECEIVED                      = 1005
    ABNORMAL_CLOSURE                        = 1006
    INVALID_FRAME_PAYLOAD_DATA              = 1007
    POLICY_VIOLATION                        = 1008
    MESSAGE_TOO_BIG                         = 1009
    MANDATORY_EXTENSION                     = 1010
    INTERNAL_ERROR                          = 1011
    SERVICE_RESTART                         = 1012
    TRY_AGAIN_LATER                         = 1013
    BAD_GATEWAY                             = 1014
    TLS_HANDSHAKE                           = 1015
