from datetime import datetime
import math
from pathlib import Path
import sys
from typing import Literal
import uuid
from pydantic import BaseModel, ConfigDict, Field, field_validator

_REPO_ROOT = Path(__file__).resolve().parents[3]
if str(_REPO_ROOT) not in sys.path:
    sys.path.append(str(_REPO_ROOT))

from ml.preprocessing.crop_yield_features import (  # noqa: E402
    canonicalize_crop,
    canonicalize_season,
    canonicalize_state,
)


class CropYieldRequest(BaseModel):
    """Leak-free yield prediction request schema (Production is strictly forbidden)."""

    model_config = ConfigDict(extra="forbid")

    farm_id: uuid.UUID | None = None
    crop: str = Field(min_length=1, max_length=80)
    crop_year: int = Field(ge=1990, le=2100)
    season: str = Field(min_length=1, max_length=40)
    state: str = Field(min_length=2, max_length=80)
    area_hectares: float = Field(gt=0.0, le=10_000_000.0, allow_inf_nan=False)
    annual_rainfall_mm: float = Field(ge=0.0, le=20_000.0, allow_inf_nan=False)
    fertilizer_kg: float = Field(ge=0.0, le=1_000_000_000.0, allow_inf_nan=False)
    pesticide_kg: float = Field(ge=0.0, le=100_000_000.0, allow_inf_nan=False)

    @field_validator("crop")
    @classmethod
    def validate_crop(cls, value: str) -> str:
        return canonicalize_crop(value)

    @field_validator("season")
    @classmethod
    def validate_season(cls, value: str) -> str:
        return canonicalize_season(value)

    @field_validator("state")
    @classmethod
    def validate_state(cls, value: str) -> str:
        return canonicalize_state(value)

    @field_validator(
        "area_hectares", "annual_rainfall_mm", "fertilizer_kg", "pesticide_kg"
    )
    @classmethod
    def ensure_finite_float(cls, value: float) -> float:
        if not math.isfinite(value):
            raise ValueError("Numeric agricultural inputs must be finite numbers.")
        return value


class FeatureDriverOut(BaseModel):
    feature: str
    impact_pct: float
    direction: Literal["positive", "negative", "neutral"]


class CropYieldResponse(BaseModel):
    id: uuid.UUID
    farm_id: uuid.UUID | None = None
    crop: str
    state: str
    season: str
    crop_year: int
    area_hectares: float
    predicted_yield: float
    yield_unit: str
    estimated_total_production: float
    production_unit: str
    model_name: str
    model_version: str
    feature_drivers: list[FeatureDriverOut]
    advisory_note: str
    created_at: datetime
    source_mode: Literal["live_api"] = "live_api"
