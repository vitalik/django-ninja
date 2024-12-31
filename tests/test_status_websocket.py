import pytest
from ninja.status import WebSocketStatus

def test_websocket_status_enum_values():
    assert WebSocketStatus.NORMAL_CLOSURE.value == 1000
    assert WebSocketStatus.GOING_AWAY.value == 1001
    assert WebSocketStatus.PROTOCOL_ERROR.value == 1002
    assert WebSocketStatus.UNSUPPORTED_DATA.value == 1003
    assert WebSocketStatus.NO_STATUS_RECEIVED.value == 1005
    assert WebSocketStatus.ABNORMAL_CLOSURE.value == 1006
    assert WebSocketStatus.INTERNAL_ERROR.value == 1011

def test_websocket_status_enum_names():
    assert WebSocketStatus.NORMAL_CLOSURE.name == "NORMAL_CLOSURE"
    assert WebSocketStatus.GOING_AWAY.name == "GOING_AWAY"
    assert WebSocketStatus.PROTOCOL_ERROR.name == "PROTOCOL_ERROR"
    assert WebSocketStatus.UNSUPPORTED_DATA.name == "UNSUPPORTED_DATA"
    assert WebSocketStatus.NO_STATUS_RECEIVED.name == "NO_STATUS_RECEIVED"
    assert WebSocketStatus.ABNORMAL_CLOSURE.name == "ABNORMAL_CLOSURE"
    assert WebSocketStatus.INTERNAL_ERROR.name == "INTERNAL_ERROR"

def test_websocket_status_enum_iteration():
    status_codes = list(WebSocketStatus)
    assert len(status_codes) == 16
    assert WebSocketStatus.NORMAL_CLOSURE in status_codes

def test_invalid_websocket_status():
    with pytest.raises(ValueError):
        WebSocketStatus(9999)
