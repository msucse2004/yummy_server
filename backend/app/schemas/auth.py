"""인증 관련 스키마"""
from pydantic import BaseModel, Field, field_validator


class SignupRequest(BaseModel):
    username: str = Field(..., min_length=1, max_length=64, description="한글, 영문, 숫자 등 다국어 문자 지원")
    password: str = Field(..., min_length=4)
    display_name: str = Field(..., min_length=1, max_length=128)
    phone: str = Field(..., min_length=1, max_length=32)
    preferred_locale: str | None = Field(None, max_length=64)


class ChangePasswordRequest(BaseModel):
    current_password: str = Field(..., min_length=1)
    new_password: str = Field(..., min_length=4)


class LoginRequest(BaseModel):
    username: str = Field(..., min_length=1, max_length=64, description="한글, 영문, 숫자 등 다국어 문자 지원")
    password: str = Field(..., min_length=1)


class UserResponse(BaseModel):
    id: int
    username: str
    role: str
    display_name: str | None
    ssn: str | None = None
    phone: str | None = None
    resume: str | None = None
    department: str | None = None
    status: str | None = None
    preferred_locale: str | None = None
    must_change_password: bool = False

    @field_validator("role", mode="before")
    @classmethod
    def role_to_str(cls, v: object) -> str:
        if hasattr(v, "value"):
            return str(v.value)
        return str(v)

    model_config = {"from_attributes": True}
