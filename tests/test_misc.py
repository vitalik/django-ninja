from pydantic import BaseModel
from ninja.signature.details import is_pydantic_model


def test_is_pydantic_model():
    class Model(BaseModel):
        x: int

    assert is_pydantic_model(Model)
    assert is_pydantic_model("instance") is False
