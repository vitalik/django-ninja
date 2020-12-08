from ninja.errors import ConfigError
import pytest
from pydantic import ValidationError, BaseModel
from ninja import NinjaAPI
from client import NinjaClient
from typing import List, Union


api = NinjaAPI(hide_get_values_errors=True)


@api.get("/check_int", response=int)
def check_int(request, a: int):
    return a


client = NinjaClient(api)


@pytest.mark.parametrize(
    "path,expected_status,expected_response",
    [
        ("/check_int", 422, "Values validation error hidden"),
        ("/check_int?a=1", 200, 1),
    ]
)
def test_hidden_values_errors(path, expected_status, expected_response):
    response = client.get(path)
    assert response.status_code == expected_status
    assert response.json() == expected_response
