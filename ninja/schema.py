from pydantic import BaseModel, validator


# Since "Model" word would be very confusing
# when used in django contetext
# this module basicaly makes alias for it named Schema

Schema = BaseModel
