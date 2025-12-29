from pydantic import BaseModel, ConfigDict


class UserCreate(BaseModel):
    telegram_id: int
    first_name: str
    last_name: str

class UserResponse(UserCreate):
    id: int
    model_config = ConfigDict(from_attributes=True)

class ScoreCreate(BaseModel):
    telegram_id: int
    subject: str
    score: int

class ScoreResponse(BaseModel):
    subject: str
    score: int
    model_config = ConfigDict(from_attributes=True)
