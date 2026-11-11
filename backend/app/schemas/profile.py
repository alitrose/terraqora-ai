from typing import Literal
import uuid
from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.schemas.auth import SupportedLanguage

PreferredUnits = Literal["metric", "imperial"]


def _clean_optional_str(value: str | None) -> str | None:
    if value is None:
        return None
    stripped = value.strip()
    return stripped or None


class FarmerProfileOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    user_id: uuid.UUID
    phone: str | None = None
    state: str | None = None
    district: str | None = None
    experience_years: int | None = None
    primary_soil_type: str | None = None
    preferred_units: PreferredUnits = "metric"
    preferred_language: SupportedLanguage = "en"


class FarmerProfileUpdate(BaseModel):
    phone: str | None = Field(default=None, max_length=24)
    state: str | None = Field(default=None, max_length=80)
    district: str | None = Field(default=None, max_length=80)
    experience_years: int | None = Field(default=None, ge=0, le=90)
    primary_soil_type: str | None = Field(default=None, max_length=60)
    preferred_units: PreferredUnits | None = None
    preferred_language: SupportedLanguage | None = None

    @field_validator("phone", "state", "district", "primary_soil_type", mode="before")
    @classmethod
    def clean_optional_fields(cls, v: str | None) -> str | None:
        return _clean_optional_str(v) if isinstance(v, str) else v

    @field_validator("phone")
    @classmethod
    def validate_phone(cls, v: str | None) -> str | None:
        if v is None:
            return None
        digits = sum(ch.isdigit() for ch in v)
        if digits < 6:
            raise ValueError("Phone number must contain at least 6 digits.")
        return v

    @field_validator("preferred_units")
    @classmethod
    def forbid_null_units(cls, v: PreferredUnits | None) -> PreferredUnits:
        if v is None:
            raise ValueError("preferred_units cannot be null.")
        return v

    @field_validator("preferred_language")
    @classmethod
    def forbid_null_language(cls, v: SupportedLanguage | None) -> SupportedLanguage:
        if v is None:
            raise ValueError("preferred_language cannot be null.")
        return v
