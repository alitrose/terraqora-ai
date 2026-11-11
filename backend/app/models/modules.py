from datetime import datetime, timezone
from typing import Any
import uuid
from sqlalchemy import (
    Boolean,
    CHAR,
    CheckConstraint,
    DateTime,
    Double,
    ForeignKey,
    Index,
    Integer,
    JSON,
    String,
    Text,
    Uuid,
    false,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base

JSONVariant = JSON().with_variant(JSONB(), "postgresql")


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class CropPrediction(Base):
    __tablename__ = "crop_predictions"
    __table_args__ = (
        CheckConstraint("crop_year >= 1990 AND crop_year <= 2100", name="ck_cp_year"),
        CheckConstraint("area_hectares > 0", name="ck_cp_area"),
        CheckConstraint("annual_rainfall_mm >= 0", name="ck_cp_rain"),
        CheckConstraint("fertilizer_kg >= 0", name="ck_cp_fert"),
        CheckConstraint("pesticide_kg >= 0", name="ck_cp_pest"),
        CheckConstraint("predicted_yield >= 0", name="ck_cp_yield"),
        Index("ix_crop_predictions_user_created", "user_id", "created_at"),
        Index("ix_crop_predictions_crop_state", "crop", "state"),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    farm_id: Mapped[uuid.UUID | None] = mapped_column(Uuid(as_uuid=True), ForeignKey("farms.id", ondelete="SET NULL"), nullable=True)
    crop: Mapped[str] = mapped_column(String(80), nullable=False)
    crop_year: Mapped[int] = mapped_column(Integer, nullable=False)
    season: Mapped[str] = mapped_column(String(40), nullable=False)
    state: Mapped[str] = mapped_column(String(80), nullable=False)
    area_hectares: Mapped[float] = mapped_column(Double, nullable=False)
    annual_rainfall_mm: Mapped[float] = mapped_column(Double, nullable=False)
    fertilizer_kg: Mapped[float] = mapped_column(Double, nullable=False)
    pesticide_kg: Mapped[float] = mapped_column(Double, nullable=False)
    predicted_yield: Mapped[float] = mapped_column(Double, nullable=False)
    yield_unit: Mapped[str] = mapped_column(String(32), nullable=False, default="tonnes/hectare", server_default="tonnes/hectare")
    estimated_total_production: Mapped[float | None] = mapped_column(Double, nullable=True)
    model_name: Mapped[str] = mapped_column(String(64), nullable=False)
    model_version: Mapped[str] = mapped_column(String(32), nullable=False)
    feature_importance_json: Mapped[dict[str, Any]] = mapped_column(JSONVariant, nullable=False, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=_utcnow, server_default=func.now())

    user: Mapped["User"] = relationship(back_populates="crop_predictions")


class DiseaseDetection(Base):
    __tablename__ = "disease_detections"
    __table_args__ = (
        CheckConstraint("image_size_bytes > 0", name="ck_dd_size"),
        CheckConstraint("confidence >= 0 AND confidence <= 1", name="ck_dd_confidence"),
        Index("ix_disease_detections_user_created", "user_id", "created_at"),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    farm_id: Mapped[uuid.UUID | None] = mapped_column(Uuid(as_uuid=True), ForeignKey("farms.id", ondelete="SET NULL"), nullable=True)
    crop_hint: Mapped[str | None] = mapped_column(String(80), nullable=True)
    image_filename: Mapped[str] = mapped_column(String(255), nullable=False)
    image_mime_type: Mapped[str] = mapped_column(String(64), nullable=False)
    image_size_bytes: Mapped[int] = mapped_column(Integer, nullable=False)
    image_sha256: Mapped[str] = mapped_column(CHAR(64), nullable=False)
    predicted_label: Mapped[str] = mapped_column(String(120), nullable=False)
    confidence: Mapped[float] = mapped_column(Double, nullable=False)
    is_uncertain: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, server_default=false())
    top_predictions_json: Mapped[list[dict[str, Any]]] = mapped_column(JSONVariant, nullable=False, default=list)
    treatment_summary: Mapped[str] = mapped_column(Text, nullable=False)
    prevention_notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    model_version: Mapped[str] = mapped_column(String(32), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=_utcnow, server_default=func.now())

    user: Mapped["User"] = relationship(back_populates="disease_detections")


class FertilizerRecommendation(Base):
    __tablename__ = "fertilizer_recommendations"
    __table_args__ = (
        CheckConstraint("nitrogen >= 0", name="ck_fr_n"),
        CheckConstraint("phosphorus >= 0", name="ck_fr_p"),
        CheckConstraint("potassium >= 0", name="ck_fr_k"),
        CheckConstraint("soil_ph >= 0 AND soil_ph <= 14", name="ck_fr_ph"),
        CheckConstraint("confidence IS NULL OR (confidence >= 0 AND confidence <= 1)", name="ck_fr_conf"),
        Index("ix_fertilizer_recs_user_created", "user_id", "created_at"),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    farm_id: Mapped[uuid.UUID | None] = mapped_column(Uuid(as_uuid=True), ForeignKey("farms.id", ondelete="SET NULL"), nullable=True)
    nitrogen: Mapped[float] = mapped_column(Double, nullable=False)
    phosphorus: Mapped[float] = mapped_column(Double, nullable=False)
    potassium: Mapped[float] = mapped_column(Double, nullable=False)
    soil_ph: Mapped[float] = mapped_column(Double, nullable=False)
    soil_type: Mapped[str] = mapped_column(String(60), nullable=False)
    crop_type: Mapped[str] = mapped_column(String(80), nullable=False)
    location: Mapped[str | None] = mapped_column(String(120), nullable=True)
    recommended_fertilizer: Mapped[str] = mapped_column(String(100), nullable=False)
    confidence: Mapped[float | None] = mapped_column(Double, nullable=True)
    nutrient_status_json: Mapped[dict[str, Any]] = mapped_column(JSONVariant, nullable=False, default=dict)
    advisory_notes: Mapped[str] = mapped_column(Text, nullable=False)
    expert_disclaimer: Mapped[str] = mapped_column(Text, nullable=False)
    model_version: Mapped[str] = mapped_column(String(32), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=_utcnow, server_default=func.now())

    user: Mapped["User"] = relationship(back_populates="fertilizer_recommendations")


class IrrigationRecommendation(Base):
    __tablename__ = "irrigation_recommendations"
    __table_args__ = (
        CheckConstraint("latitude >= -90 AND latitude <= 90", name="ck_ir_lat"),
        CheckConstraint("longitude >= -180 AND longitude <= 180", name="ck_ir_lon"),
        CheckConstraint("forecast_rainfall_7d_mm >= 0", name="ck_ir_rain"),
        CheckConstraint("estimated_et0_mm >= 0", name="ck_ir_et0"),
        CheckConstraint("recommended_water_mm >= 0", name="ck_ir_water"),
        CheckConstraint(
            "irrigation_urgency IN ('low', 'moderate', 'high', 'skip_rain_expected')",
            name="ck_ir_urgency",
        ),
        Index("ix_irrigation_recs_user_created", "user_id", "created_at"),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    farm_id: Mapped[uuid.UUID | None] = mapped_column(Uuid(as_uuid=True), ForeignKey("farms.id", ondelete="SET NULL"), nullable=True)
    location_name: Mapped[str] = mapped_column(String(120), nullable=False)
    latitude: Mapped[float] = mapped_column(Double, nullable=False)
    longitude: Mapped[float] = mapped_column(Double, nullable=False)
    crop_type: Mapped[str] = mapped_column(String(80), nullable=False)
    growth_stage: Mapped[str] = mapped_column(String(40), nullable=False, default="mid_season", server_default="mid_season")
    weather_provider: Mapped[str] = mapped_column(String(40), nullable=False)
    weather_snapshot_json: Mapped[dict[str, Any]] = mapped_column(JSONVariant, nullable=False)
    forecast_rainfall_7d_mm: Mapped[float] = mapped_column(Double, nullable=False)
    estimated_et0_mm: Mapped[float] = mapped_column(Double, nullable=False)
    recommended_water_mm: Mapped[float] = mapped_column(Double, nullable=False)
    irrigation_urgency: Mapped[str] = mapped_column(String(24), nullable=False)
    is_sensor_backed: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, server_default=false())
    advisory_notes: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=_utcnow, server_default=func.now())

    user: Mapped["User"] = relationship(back_populates="irrigation_recommendations")


class CropRecommendation(Base):
    __tablename__ = "crop_recommendations"
    __table_args__ = (
        CheckConstraint("nitrogen >= 0", name="ck_cr_n"),
        CheckConstraint("phosphorus >= 0", name="ck_cr_p"),
        CheckConstraint("potassium >= 0", name="ck_cr_k"),
        CheckConstraint("humidity_pct >= 0 AND humidity_pct <= 100", name="ck_cr_hum"),
        CheckConstraint("soil_ph >= 0 AND soil_ph <= 14", name="ck_cr_ph"),
        CheckConstraint("rainfall_mm >= 0", name="ck_cr_rain"),
        Index("ix_crop_recs_user_created", "user_id", "created_at"),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    farm_id: Mapped[uuid.UUID | None] = mapped_column(Uuid(as_uuid=True), ForeignKey("farms.id", ondelete="SET NULL"), nullable=True)
    nitrogen: Mapped[float] = mapped_column(Double, nullable=False)
    phosphorus: Mapped[float] = mapped_column(Double, nullable=False)
    potassium: Mapped[float] = mapped_column(Double, nullable=False)
    temperature_c: Mapped[float] = mapped_column(Double, nullable=False)
    humidity_pct: Mapped[float] = mapped_column(Double, nullable=False)
    soil_ph: Mapped[float] = mapped_column(Double, nullable=False)
    rainfall_mm: Mapped[float] = mapped_column(Double, nullable=False)
    season: Mapped[str | None] = mapped_column(String(40), nullable=True)
    region: Mapped[str | None] = mapped_column(String(80), nullable=True)
    recommended_crop: Mapped[str] = mapped_column(String(80), nullable=False)
    top_candidates_json: Mapped[list[dict[str, Any]]] = mapped_column(JSONVariant, nullable=False, default=list)
    model_version: Mapped[str] = mapped_column(String(32), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=_utcnow, server_default=func.now())

    user: Mapped["User"] = relationship(back_populates="crop_recommendations")


class ChatSession(Base):
    __tablename__ = "chat_sessions"
    __table_args__ = (
        CheckConstraint("language IN ('en', 'ta', 'ml', 'hi', 'te')", name="ck_cs_lang"),
        Index("ix_chat_sessions_user_updated", "user_id", "updated_at"),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    farm_id: Mapped[uuid.UUID | None] = mapped_column(Uuid(as_uuid=True), ForeignKey("farms.id", ondelete="SET NULL"), nullable=True)
    title: Mapped[str] = mapped_column(String(160), nullable=False, default="New Farming Consultation", server_default="New Farming Consultation")
    language: Mapped[str] = mapped_column(String(8), nullable=False, default="en", server_default="en")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=_utcnow, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=_utcnow, onupdate=_utcnow, server_default=func.now())

    user: Mapped["User"] = relationship(back_populates="chat_sessions")
    messages: Mapped[list["ChatMessage"]] = relationship(
        back_populates="session",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )


class ChatMessage(Base):
    __tablename__ = "chat_messages"
    __table_args__ = (
        CheckConstraint("role IN ('user', 'assistant', 'system')", name="ck_cm_role"),
        CheckConstraint("latency_ms IS NULL OR latency_ms >= 0", name="ck_cm_latency"),
        Index("ix_chat_messages_session_created", "session_id", "created_at"),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    session_id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), ForeignKey("chat_sessions.id", ondelete="CASCADE"), nullable=False)
    role: Mapped[str] = mapped_column(String(20), nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    citations_json: Mapped[list[dict[str, Any]]] = mapped_column(JSONVariant, nullable=False, default=list)
    provider: Mapped[str | None] = mapped_column(String(32), nullable=True)
    model_name: Mapped[str | None] = mapped_column(String(64), nullable=True)
    latency_ms: Mapped[int | None] = mapped_column(Integer, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=_utcnow, server_default=func.now())

    session: Mapped["ChatSession"] = relationship(back_populates="messages")


class GeneratedReport(Base):
    __tablename__ = "generated_reports"
    __table_args__ = (Index("ix_generated_reports_user_created", "user_id", "created_at"),)

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    farm_id: Mapped[uuid.UUID | None] = mapped_column(Uuid(as_uuid=True), ForeignKey("farms.id", ondelete="SET NULL"), nullable=True)
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    crop_prediction_id: Mapped[uuid.UUID | None] = mapped_column(Uuid(as_uuid=True), ForeignKey("crop_predictions.id", ondelete="SET NULL"), nullable=True)
    fertilizer_recommendation_id: Mapped[uuid.UUID | None] = mapped_column(Uuid(as_uuid=True), ForeignKey("fertilizer_recommendations.id", ondelete="SET NULL"), nullable=True)
    irrigation_recommendation_id: Mapped[uuid.UUID | None] = mapped_column(Uuid(as_uuid=True), ForeignKey("irrigation_recommendations.id", ondelete="SET NULL"), nullable=True)
    report_payload_json: Mapped[dict[str, Any]] = mapped_column(JSONVariant, nullable=False)
    ai_summary: Mapped[str] = mapped_column(Text, nullable=False)
    pdf_filename: Mapped[str] = mapped_column(String(255), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=_utcnow, server_default=func.now())

    user: Mapped["User"] = relationship(back_populates="generated_reports")
