from datetime import datetime
from typing import Literal
import uuid
from pydantic import BaseModel, ConfigDict, Field


GrowthStageInput = Literal[
    "initial", "development", "mid_season", "late_season", "unknown"
]
IrrigationMethodInput = Literal[
    "rainfed", "drip", "sprinkler", "canal", "borewell", "mixed"
]


class WeatherIrrigationRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    farm_id: uuid.UUID | None = None
    location_name: str | None = Field(default=None, min_length=2, max_length=120)
    latitude: float | None = Field(default=None, ge=-90.0, le=90.0)
    longitude: float | None = Field(default=None, ge=-180.0, le=180.0)
    crop_type: str | None = Field(default=None, max_length=80)
    growth_stage: GrowthStageInput | None = None
    soil_type: str | None = Field(default=None, max_length=60)
    irrigation_type: IrrigationMethodInput | None = None
    soil_moisture_pct: float | None = Field(default=None, ge=0.0, le=100.0)


class DailyForecastPointOut(BaseModel):
    date: str
    temp_max_c: float
    temp_min_c: float
    humidity_pct: float
    rain_mm: float
    precipitation_probability_pct: int | None = None
    et0_mm: float


class WeatherAlertOut(BaseModel):
    severity: Literal["info", "warning", "alert"]
    title: str
    message: str


class WeatherIrrigationResponse(BaseModel):
    id: uuid.UUID
    saved_to_history: bool = True
    farm_id: uuid.UUID | None = None
    location_name: str
    latitude: float
    longitude: float
    crop_type: str | None = None
    growth_stage: str | None = None
    soil_type: str | None = None
    irrigation_type: str | None = None
    weather_provider: str
    provider_attribution: str
    observation_time: datetime
    forecast_generated_at: datetime
    observation_age_minutes: int
    freshness_status: Literal["live", "cached", "delayed"] = "live"
    cache_hit: bool = False
    units_summary: dict[str, str]
    current_temp_c: float
    current_humidity_pct: float
    wind_speed_kmh: float
    weather_condition: str
    forecast_rainfall_7d_mm: float
    estimated_et0_mm: float
    recommended_water_mm: float | None = None
    schedule_status: Literal[
        "computed", "insufficient_agronomic_inputs", "rainfed_advisory"
    ] = "computed"
    irrigation_urgency: Literal[
        "low", "moderate", "high", "skip_rain_expected", "insufficient_data"
    ]
    is_sensor_backed: bool = False
    sensor_notice: str
    missing_inputs: list[str] = Field(default_factory=list)
    assumptions: list[str] = Field(default_factory=list)
    advisory_notes: str
    alerts: list[WeatherAlertOut] = Field(default_factory=list)
    forecast_7d: list[DailyForecastPointOut] = Field(default_factory=list)
    created_at: datetime
    source_mode: Literal["live_api"] = "live_api"
