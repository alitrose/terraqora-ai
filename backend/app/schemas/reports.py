from __future__ import annotations

from datetime import datetime
from typing import Any, Literal
import uuid
from pydantic import BaseModel, ConfigDict, Field

from app.schemas.auth import SupportedLanguage

ReportType = Literal[
    "combined_intelligence",
    "crop_yield",
    "crop_recommendation",
    "fertilizer_recommendation",
    "disease_detection",
    "weather_irrigation",
]


class ReportCreateRequest(BaseModel):
    title: str = Field(min_length=3, max_length=200)
    report_type: ReportType = "combined_intelligence"
    farm_id: uuid.UUID | None = None

    # Optional references to existing database records
    crop_prediction_id: uuid.UUID | None = None
    crop_recommendation_id: uuid.UUID | None = None
    fertilizer_recommendation_id: uuid.UUID | None = None
    disease_detection_id: uuid.UUID | None = None
    irrigation_recommendation_id: uuid.UUID | None = None

    # Optional manual / custom overrides (e.g. for on-the-fly advisory report generation)
    crop: str | None = None
    state: str | None = None
    season: str | None = None
    area_hectares: float | None = Field(default=None, gt=0)
    predicted_yield: float | None = Field(default=None, ge=0)
    yield_unit: str | None = None
    fertilizer_recommendation: str | None = None
    irrigation_summary: str | None = None
    language: SupportedLanguage = "en"


class GeneratedReportResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    title: str
    report_type: str
    farm_id: uuid.UUID | None = None
    farm_name: str | None = None
    crop: str | None = None
    state: str | None = None
    season: str | None = None
    area_hectares: float | None = None
    predicted_yield: float | None = None
    yield_unit: str = "tonnes/hectare"
    model_explanation: str = ""
    agricultural_observations: list[str] = Field(default_factory=list)
    fertilizer_recommendation: str | None = None
    irrigation_summary: str | None = None
    ai_summary: str
    pdf_filename: str
    download_url: str
    created_at: datetime
    source_mode: Literal["live_api"] = "live_api"
