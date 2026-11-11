from datetime import datetime, timezone
import uuid
from sqlalchemy import (
    Boolean,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    Uuid,
    false,
    func,
    true,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class User(Base):
    __tablename__ = "users"
    __table_args__ = (
        CheckConstraint("role IN ('farmer', 'admin')", name="ck_users_role"),
        CheckConstraint(
            "preferred_language IN ('en', 'ta', 'ml', 'hi', 'te')",
            name="ck_users_preferred_language",
        ),
        Index("ix_users_role", "role"),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    email: Mapped[str] = mapped_column(String(255), nullable=False, unique=True)
    hashed_password: Mapped[str] = mapped_column(String(255), nullable=False)
    full_name: Mapped[str] = mapped_column(String(120), nullable=False)
    role: Mapped[str] = mapped_column(String(20), nullable=False, default="farmer", server_default="farmer")
    preferred_language: Mapped[str] = mapped_column(String(8), nullable=False, default="en", server_default="en")
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True, server_default=true())
    last_login_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=_utcnow, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=_utcnow, onupdate=_utcnow, server_default=func.now()
    )

    profile: Mapped["FarmerProfile | None"] = relationship(
        back_populates="user",
        uselist=False,
        cascade="all, delete-orphan",
        passive_deletes=True,
    )
    farms: Mapped[list["Farm"]] = relationship(
        back_populates="user",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )
    crop_predictions: Mapped[list["CropPrediction"]] = relationship(
        back_populates="user",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )
    disease_detections: Mapped[list["DiseaseDetection"]] = relationship(
        back_populates="user",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )
    fertilizer_recommendations: Mapped[list["FertilizerRecommendation"]] = relationship(
        back_populates="user",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )
    irrigation_recommendations: Mapped[list["IrrigationRecommendation"]] = relationship(
        back_populates="user",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )
    crop_recommendations: Mapped[list["CropRecommendation"]] = relationship(
        back_populates="user",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )
    chat_sessions: Mapped[list["ChatSession"]] = relationship(
        back_populates="user",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )
    generated_reports: Mapped[list["GeneratedReport"]] = relationship(
        back_populates="user",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )


class FarmerProfile(Base):
    __tablename__ = "farmer_profiles"
    __table_args__ = (
        CheckConstraint(
            "experience_years IS NULL OR experience_years >= 0",
            name="ck_farmer_profiles_experience_years",
        ),
        CheckConstraint(
            "preferred_units IN ('metric', 'imperial')",
            name="ck_farmer_profiles_preferred_units",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
    )
    phone: Mapped[str | None] = mapped_column(String(24), nullable=True)
    state: Mapped[str | None] = mapped_column(String(80), nullable=True)
    district: Mapped[str | None] = mapped_column(String(80), nullable=True)
    experience_years: Mapped[int | None] = mapped_column(Integer, nullable=True)
    primary_soil_type: Mapped[str | None] = mapped_column(String(60), nullable=True)
    preferred_units: Mapped[str] = mapped_column(
        String(20), nullable=False, default="metric", server_default="metric"
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=_utcnow, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=_utcnow, onupdate=_utcnow, server_default=func.now()
    )

    user: Mapped["User"] = relationship(back_populates="profile")
