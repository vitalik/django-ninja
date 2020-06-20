from pydantic import BaseModel
from ninja.operation import is_pydantic_model


def test_is_pydantic_model():
    class Model(BaseModel):
        x: int

    assert is_pydantic_model(Model)
    assert is_pydantic_model("instance") is False
