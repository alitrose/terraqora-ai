from datetime import datetime, timezone
import uuid
from sqlalchemy import (
    CheckConstraint,
    DateTime,
    Double,
    ForeignKey,
    Index,
    String,
    Uuid,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class Farm(Base):
    __tablename__ = "farms"
    __table_args__ = (
        CheckConstraint(
            "latitude IS NULL OR (latitude >= -90 AND latitude <= 90)",
            name="ck_farms_latitude",
        ),
        CheckConstraint(
            "longitude IS NULL OR (longitude >= -180 AND longitude <= 180)",
            name="ck_farms_longitude",
        ),
        CheckConstraint("area_hectares > 0", name="ck_farms_area_positive"),
        CheckConstraint(
            "soil_ph IS NULL OR (soil_ph >= 0 AND soil_ph <= 14)",
            name="ck_farms_soil_ph",
        ),
        CheckConstraint(
            "irrigation_type IS NULL OR irrigation_type IN ('rainfed', 'drip', 'sprinkler', 'canal', 'borewell', 'mixed')",
            name="ck_farms_irrigation_type",
        ),
        Index("ix_farms_user_id", "user_id"),
        Index("ix_farms_state", "state"),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    state: Mapped[str] = mapped_column(String(80), nullable=False)
    district: Mapped[str | None] = mapped_column(String(80), nullable=True)
    latitude: Mapped[float | None] = mapped_column(Double, nullable=True)
    longitude: Mapped[float | None] = mapped_column(Double, nullable=True)
    area_hectares: Mapped[float] = mapped_column(Double, nullable=False)
    soil_type: Mapped[str | None] = mapped_column(String(60), nullable=True)
    soil_ph: Mapped[float | None] = mapped_column(Double, nullable=True)
    irrigation_type: Mapped[str | None] = mapped_column(String(40), nullable=True)
    primary_crop: Mapped[str | None] = mapped_column(String(80), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=_utcnow, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=_utcnow, onupdate=_utcnow, server_default=func.now()
    )

    user: Mapped["User"] = relationship(back_populates="farms")
