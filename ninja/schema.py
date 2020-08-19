import pydantic
from pydantic import BaseModel, validator


pydantic_version = list(map(int, pydantic.VERSION.split(".")))[:2]
assert pydantic_version >= [1, 6], "Pydantic 1.6+"


# Since "Model" word would be very confusing
# when used in django context
# this module basicaly makes alias for it named Schema


class Schema(BaseModel):
    class Config:
        orm_mode = True
