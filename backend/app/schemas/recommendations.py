from datetime import datetime
import math
from typing import Literal
import uuid
from pydantic import BaseModel, ConfigDict, Field, field_validator


class CropRecommendationRequest(BaseModel):
    """Crop suitability request backed by 7 validated soil & climate ML features."""

    model_config = ConfigDict(extra="forbid")

    farm_id: uuid.UUID | None = None
    nitrogen: float = Field(ge=0.0, le=500.0, allow_inf_nan=False)
    phosphorus: float = Field(ge=0.0, le=500.0, allow_inf_nan=False)
    potassium: float = Field(ge=0.0, le=500.0, allow_inf_nan=False)
    temperature_c: float = Field(ge=-10.0, le=60.0, allow_inf_nan=False)
    humidity_pct: float = Field(ge=0.0, le=100.0, allow_inf_nan=False)
    soil_ph: float = Field(ge=0.0, le=14.0, allow_inf_nan=False)
    rainfall_mm: float = Field(ge=0.0, le=5000.0, allow_inf_nan=False)
    season: str | None = Field(default=None, max_length=40)
    region: str | None = Field(default=None, max_length=80)

    @field_validator(
        "nitrogen",
        "phosphorus",
        "potassium",
        "temperature_c",
        "humidity_pct",
        "soil_ph",
        "rainfall_mm",
    )
    @classmethod
    def ensure_finite_float(cls, value: float) -> float:
        if not math.isfinite(value):
            raise ValueError("Numeric agricultural readings must be finite numbers.")
        return value

    @field_validator("season", "region")
    @classmethod
    def trim_optional_text(cls, value: str | None) -> str | None:
        if value is None:
            return None
        cleaned = value.strip()
        return cleaned or None


class CropCandidateOut(BaseModel):
    crop: str
    probability: float
    fit_reason: str


class CropRecommendationResponse(BaseModel):
    id: uuid.UUID
    farm_id: uuid.UUID | None = None
    nitrogen: float
    phosphorus: float
    potassium: float
    temperature_c: float
    humidity_pct: float
    soil_ph: float
    rainfall_mm: float
    season: str | None = None
    region: str | None = None
    recommended_crop: str
    top_candidates: list[CropCandidateOut]
    soil_climate_summary: str
    model_version: str
    created_at: datetime
    source_mode: Literal["live_api"] = "live_api"


class FertilizerRequest(BaseModel):
    """Fertilizer formulation & agronomic soil-sufficiency assessment request."""

    model_config = ConfigDict(extra="forbid")

    farm_id: uuid.UUID | None = None
    nitrogen: float = Field(ge=0.0, le=500.0, allow_inf_nan=False)
    phosphorus: float = Field(ge=0.0, le=500.0, allow_inf_nan=False)
    potassium: float = Field(ge=0.0, le=500.0, allow_inf_nan=False)
    soil_ph: float = Field(ge=0.0, le=14.0, allow_inf_nan=False)
    soil_type: str = Field(min_length=1, max_length=60)
    crop_type: str = Field(min_length=1, max_length=80)
    location: str | None = Field(default=None, max_length=120)

    @field_validator("nitrogen", "phosphorus", "potassium", "soil_ph")
    @classmethod
    def ensure_finite_float(cls, value: float) -> float:
        if not math.isfinite(value):
            raise ValueError("Numeric soil test values must be finite numbers.")
        return value

    @field_validator("soil_type", "crop_type")
    @classmethod
    def clean_required_text(cls, value: str) -> str:
        cleaned = value.strip()
        if not cleaned:
            raise ValueError("Soil type and crop type cannot be blank.")
        return cleaned

    @field_validator("location")
    @classmethod
    def clean_optional_location(cls, value: str | None) -> str | None:
        if value is None:
            return None
        cleaned = value.strip()
        return cleaned or None


class NutrientLevelOut(BaseModel):
    nutrient: str
    value: float
    optimal_min: float
    optimal_max: float
    status: Literal["low", "optimal", "high"]


class FertilizerResponse(BaseModel):
    id: uuid.UUID
    farm_id: uuid.UUID | None = None
    nitrogen: float
    phosphorus: float
    potassium: float
    soil_ph: float
    soil_type: str
    crop_type: str
    location: str | None = None
    recommended_fertilizer: str
    confidence: float
    ml_predicted_grade: str | None = None
    recommendation_mode: Literal[
        "ml_grade_with_agronomic_guardrails", "agronomic_sufficiency_guardrail"
    ] = "ml_grade_with_agronomic_guardrails"
    dataset_coverage_note: str
    nutrient_levels: list[NutrientLevelOut]
    ph_assessment: str
    advisory_notes: str
    expert_disclaimer: str
    model_version: str
    created_at: datetime
    source_mode: Literal["live_api"] = "live_api"
