from __future__ import annotations

from datetime import datetime
from typing import Any, Literal
import uuid
from pydantic import BaseModel, ConfigDict, Field


class ModuleActivitySummary(BaseModel):
    yield_predictions: int = 0
    crop_recommendations: int = 0
    fertilizer_recommendations: int = 0
    disease_detections: int = 0
    irrigation_advisories: int = 0
    ai_chat_sessions: int = 0
    total_activities: int = 0
    active_farms_count: int = 0
    total_hectares_managed: float = 0.0


class DailyActivityPoint(BaseModel):
    date: str  # YYYY-MM-DD
    yield_predictions: int = 0
    crop_recommendations: int = 0
    fertilizer_recommendations: int = 0
    disease_detections: int = 0
    irrigation_advisories: int = 0
    total: int = 0


class CropActivityBreakdown(BaseModel):
    crop: str
    count: int
    avg_yield: float | None = None
    yield_unit: str | None = None


class DiseaseActivityBreakdown(BaseModel):
    label: str
    crop_name: str
    disease_name: str
    count: int
    uncertain_count: int = 0
    avg_confidence: float = 0.0


class FertilizerActivityBreakdown(BaseModel):
    recommended_fertilizer: str
    count: int


class FarmActivityBreakdown(BaseModel):
    farm_id: str
    farm_name: str
    state: str
    area_hectares: float
    total_activities: int
    last_activity: datetime | None = None


class UserOperationalAnalyticsResponse(BaseModel):
    summary: ModuleActivitySummary
    filter_range_days: int
    filter_farm_id: uuid.UUID | None = None
    filter_farm_name: str | None = None
    timeline: list[DailyActivityPoint]
    top_crops: list[CropActivityBreakdown]
    disease_findings: list[DiseaseActivityBreakdown]
    fertilizer_grades: list[FertilizerActivityBreakdown]
    farm_breakdown: list[FarmActivityBreakdown]
    source_mode: Literal["live_api"] = "live_api"


# --- Macro / Dataset Analytics Schemas (Preserving Dataset Benchmark Explorations) ---

class DatasetAnalyticsFilter(BaseModel):
    crop: str | None = None
    state: str | None = None
    season: str | None = None
    year_start: int | None = Field(default=2013, ge=1997, le=2020)
    year_end: int | None = Field(default=2020, ge=1997, le=2020)


class CropDistributionItem(BaseModel):
    name: str
    records: int
    avg_yield: float


class StateProductionItem(BaseModel):
    state: str
    production_mt: float
    records: int


class AnnualTrendItem(BaseModel):
    year: int
    avg_rainfall: float
    avg_yield: float
    fertilizer_index: float
    pesticide_index: float


class YieldComparisonItem(BaseModel):
    crop: str
    kharif: float
    rabi: float
    whole_year: float


class CorrelationItem(BaseModel):
    feature_x: str
    feature_y: str
    correlation: float


class DatasetAnalyticsResponse(BaseModel):
    total_records: int
    unique_crops: int
    unique_states: int
    avg_yield: float
    avg_rainfall_mm: float
    total_fertilizer_tonnes: float
    total_pesticide_tonnes: float
    crop_distribution: list[CropDistributionItem]
    state_production: list[StateProductionItem]
    annual_trends: list[AnnualTrendItem]
    yield_comparison: list[YieldComparisonItem]
    correlation_matrix: list[CorrelationItem]
    source_mode: Literal["live_api", "dataset_benchmark"] = "live_api"
