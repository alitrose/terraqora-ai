from datetime import datetime
from typing import Literal
import uuid
from pydantic import BaseModel, ConfigDict, EmailStr, field_validator

from app.schemas.auth import SupportedLanguage, UserRole


class AdminModelStatusItem(BaseModel):
    module: str
    algorithm: str
    status: str
    metric_label: str
    metric_value: str
    artifact_size: str


class AdminUserItem(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    full_name: str
    email: EmailStr
    role: UserRole
    preferred_language: SupportedLanguage
    is_active: bool
    farms_count: int
    predictions_count: int
    created_at: datetime


class AdminOverviewResponse(BaseModel):
    total_users: int
    active_farms: int
    total_predictions: int
    total_disease_scans: int
    total_ai_chats: int
    models: list[AdminModelStatusItem]
    users: list[AdminUserItem]
    source_mode: Literal["live_api"] = "live_api"


class AdminUserUpdate(BaseModel):
    role: UserRole | None = None
    is_active: bool | None = None

    @field_validator("role")
    @classmethod
    def forbid_null_role(cls, v: UserRole | None) -> UserRole:
        if v is None:
            raise ValueError("role cannot be null.")
        return v

    @field_validator("is_active")
    @classmethod
    def forbid_null_active(cls, v: bool | None) -> bool:
        if v is None:
            raise ValueError("is_active cannot be null.")
        return v
