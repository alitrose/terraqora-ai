from datetime import datetime
from typing import Literal
import uuid
from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator

SupportedLanguage = Literal["en", "ta", "ml", "hi", "te"]
UserRole = Literal["farmer", "admin"]


class RegisterRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8, max_length=72)
    full_name: str = Field(min_length=2, max_length=120)
    preferred_language: SupportedLanguage = "en"
    state: str | None = Field(default=None, max_length=80)

    @field_validator("full_name")
    @classmethod
    def strip_full_name(cls, v: str) -> str:
        cleaned = v.strip()
        if len(cleaned) < 2:
            raise ValueError("Full name must contain at least 2 non-whitespace characters.")
        return cleaned

    @field_validator("password")
    @classmethod
    def validate_password(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("Password cannot be blank.")
        if len(v.encode("utf-8")) > 72:
            raise ValueError("Password must not exceed 72 UTF-8 bytes.")
        return v


class LoginRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=1, max_length=128)


class UserOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    email: EmailStr
    full_name: str
    role: UserRole
    preferred_language: SupportedLanguage
    is_active: bool
    created_at: datetime


class AuthResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserOut
