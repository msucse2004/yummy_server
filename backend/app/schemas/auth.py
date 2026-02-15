"""인증 관련 스키마"""
from pydantic import BaseModel, Field, field_validator


class LoginRequest(BaseModel):
    username: str = Field(..., min_length=1, max_length=64)
    password: str = Field(..., min_length=1)


class UserResponse(BaseModel):
    id: int
    username: str
    role: str
    display_name: str | None

    @field_validator("role", mode="before")
    @classmethod
    def role_to_str(cls, v: object) -> str:
        if hasattr(v, "value"):
            return str(v.value)
        return str(v)

    model_config = {"from_attributes": True}
