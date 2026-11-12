from datetime import datetime
from typing import Literal
import uuid
from pydantic import BaseModel


class DiseaseCandidateOut(BaseModel):
    label: str
    confidence: float


class DiseaseDetectionResponse(BaseModel):
    id: uuid.UUID
    farm_id: uuid.UUID | None = None
    crop_hint: str | None = None
    image_filename: str
    predicted_label: str
    crop_name: str
    disease_name: str
    is_healthy: bool
    confidence: float
    top2_margin: float | None = None
    is_uncertain: bool
    uncertainty_reason: str | None = None
    top_predictions: list[DiseaseCandidateOut]
    treatment_summary: str
    prevention_notes: str
    next_steps: list[str] = []
    limitations: list[str] = []
    supported_scope_note: str = ""
    model_version: str
    created_at: datetime
    source_mode: Literal["live_api"] = "live_api"
