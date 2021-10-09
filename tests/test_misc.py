import copy
import uuid

import pytest
from pydantic import BaseModel

from ninja import NinjaAPI
from ninja.constants import NOT_SET
from ninja.signature.details import is_pydantic_model
from ninja.signature.utils import NinjaUUIDConverter
from ninja.testing import TestClient


def test_is_pydantic_model():
    class Model(BaseModel):
        x: int

    assert is_pydantic_model(Model)
    assert is_pydantic_model("instance") is False


def test_client():
    "covering evertying in testclient (includeing invalid paths)"
    api = NinjaAPI()
    client = TestClient(api)
    with pytest.raises(Exception):
        client.get("/404")


def test_kwargs():
    api = NinjaAPI()

    @api.get("/")
    def operation(request, a: str, *args, **kwargs):
        pass

    schema = api.get_openapi_schema()
    params = schema["paths"]["/api/"]["get"]["parameters"]
    print(params)
    assert params == [  # Only `a` should be here, not kwargs
        {
            "in": "query",
            "name": "a",
            "schema": {"title": "A", "type": "string"},
            "required": True,
        }
    ]


def test_uuid_converter():
    conv = NinjaUUIDConverter()
    assert isinstance(conv.to_url(uuid.uuid4()), str)


def test_copy_not_set():
    assert id(NOT_SET) == id(copy.copy(NOT_SET))
    assert id(NOT_SET) == id(copy.deepcopy(NOT_SET))
