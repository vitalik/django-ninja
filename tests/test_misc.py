import pytest
from pydantic import BaseModel
from ninja import NinjaAPI
from ninja.testing import TestClient
from ninja.signature.details import is_pydantic_model


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
        response = client.get("/404")
