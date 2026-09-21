import uuid
from datetime import datetime

from pydantic import BaseModel, Field


class SignupRequest(BaseModel):
    email: str = Field(min_length=3, max_length=255)


class SignupResponse(BaseModel):
    id: uuid.UUID
    email: str
    api_key: str  # shown exactly once - the server only ever stores its hash
    created_at: datetime
