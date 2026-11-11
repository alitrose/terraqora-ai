from datetime import datetime
from typing import Literal
import uuid
from pydantic import BaseModel, ConfigDict, Field, field_validator

IrrigationType = Literal["rainfed", "drip", "sprinkler", "canal", "borewell", "mixed"]


def _strip_optional(value: str | None) -> str | None:
    if value is None:
        return None
    stripped = value.strip()
    return stripped or None


class FarmCreate(BaseModel):
    name: str = Field(min_length=2, max_length=120)
    state: str = Field(min_length=2, max_length=80)
    district: str | None = Field(default=None, max_length=80)
    latitude: float | None = Field(default=None, ge=-90.0, le=90.0)
    longitude: float | None = Field(default=None, ge=-180.0, le=180.0)
    area_hectares: float = Field(gt=0.0, le=100000.0)
    soil_type: str | None = Field(default=None, max_length=60)
    soil_ph: float | None = Field(default=None, ge=0.0, le=14.0)
    irrigation_type: IrrigationType | None = None
    primary_crop: str | None = Field(default=None, max_length=80)

    @field_validator("name", "state")
    @classmethod
    def strip_required_text(cls, v: str) -> str:
        cleaned = v.strip()
        if len(cleaned) < 2:
            raise ValueError("Must be at least 2 characters long.")
        return cleaned

    @field_validator("district", "soil_type", "primary_crop", mode="before")
    @classmethod
    def clean_optional_text(cls, v: str | None) -> str | None:
        return _strip_optional(v) if isinstance(v, str) else v


class FarmUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=2, max_length=120)
    state: str | None = Field(default=None, min_length=2, max_length=80)
    district: str | None = Field(default=None, max_length=80)
    latitude: float | None = Field(default=None, ge=-90.0, le=90.0)
    longitude: float | None = Field(default=None, ge=-180.0, le=180.0)
    area_hectares: float | None = Field(default=None, gt=0.0, le=100000.0)
    soil_type: str | None = Field(default=None, max_length=60)
    soil_ph: float | None = Field(default=None, ge=0.0, le=14.0)
    irrigation_type: IrrigationType | None = None
    primary_crop: str | None = Field(default=None, max_length=80)

    @field_validator("name", "state")
    @classmethod
    def validate_required_if_present(cls, v: str | None) -> str:
        if v is None:
            raise ValueError("This field cannot be set to null.")
        cleaned = v.strip()
        if len(cleaned) < 2:
            raise ValueError("Must be at least 2 characters long.")
        return cleaned

    @field_validator("area_hectares")
    @classmethod
    def validate_area_if_present(cls, v: float | None) -> float:
        if v is None:
            raise ValueError("area_hectares cannot be null.")
        return v

    @field_validator("district", "soil_type", "primary_crop", mode="before")
    @classmethod
    def clean_optional_text(cls, v: str | None) -> str | None:
        return _strip_optional(v) if isinstance(v, str) else v


class FarmOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    user_id: uuid.UUID
    name: str
    state: str
    district: str | None
    latitude: float | None
    longitude: float | None
    area_hectares: float
    soil_type: str | None
    soil_ph: float | None
    irrigation_type: IrrigationType | None
    primary_crop: str | None
    created_at: datetime
    updated_at: datetime
