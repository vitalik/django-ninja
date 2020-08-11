from pydantic import BaseModel, validator


# Since "Model" word would be very confusing
# when used in django context
# this module basicaly makes alias for it named Schema


class Schema(BaseModel):
    class Config:
        orm_mode = True
