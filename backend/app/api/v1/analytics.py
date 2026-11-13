from __future__ import annotations

import uuid
from fastapi import APIRouter, Depends, Query, Request
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.core.config import get_settings
from app.core.rate_limit import limiter
from app.db.session import get_db
from app.models.user import User
from app.schemas.analytics import (
    DatasetAnalyticsFilter,
    DatasetAnalyticsResponse,
    UserOperationalAnalyticsResponse,
)
from app.services import analytics_service

settings = get_settings()
router = APIRouter(prefix="/analytics", tags=["Analytics"])


@router.get("/operational", response_model=UserOperationalAnalyticsResponse)
@limiter.limit(settings.RATE_LIMIT_DEFAULT)
def get_user_operational_analytics(
    request: Request,
    range_days: int = Query(default=30, ge=1, le=3650),
    farm_id: uuid.UUID | None = Query(default=None),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> UserOperationalAnalyticsResponse:
    _ = request
    return analytics_service.get_user_operational_analytics(
        db, current_user, range_days=range_days, farm_id=farm_id
    )


@router.get("/dataset", response_model=DatasetAnalyticsResponse)
@limiter.limit(settings.RATE_LIMIT_DEFAULT)
def get_dataset_macro_analytics(
    request: Request,
    crop: str | None = Query(default=None),
    state: str | None = Query(default=None),
    season: str | None = Query(default=None),
    year_start: int | None = Query(default=2013, ge=1997, le=2020),
    year_end: int | None = Query(default=2020, ge=1997, le=2020),
    _current_user: User = Depends(get_current_user),
) -> DatasetAnalyticsResponse:
    _ = request
    filters = DatasetAnalyticsFilter(
        crop=crop,
        state=state,
        season=season,
        year_start=year_start,
        year_end=year_end,
    )
    return analytics_service.get_dataset_macro_analytics(filters)


@router.get("/overview")
@limiter.limit(settings.RATE_LIMIT_DEFAULT)
def get_analytics_overview(
    request: Request,
    mode: str = Query(default="dataset", pattern="^(dataset|operational)$"),
    range_days: int = Query(default=30, ge=1, le=3650),
    farm_id: uuid.UUID | None = Query(default=None),
    crop: str | None = Query(default=None),
    state: str | None = Query(default=None),
    season: str | None = Query(default=None),
    year_start: int | None = Query(default=2013, ge=1997, le=2020),
    year_end: int | None = Query(default=2020, ge=1997, le=2020),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Dual-mode analytics route: returns national dataset benchmarks or real user operational intelligence."""
    _ = request
    if mode == "operational":
        return analytics_service.get_user_operational_analytics(
            db, current_user, range_days=range_days, farm_id=farm_id
        )

    filters = DatasetAnalyticsFilter(
        crop=crop,
        state=state,
        season=season,
        year_start=year_start,
        year_end=year_end,
    )
    return analytics_service.get_dataset_macro_analytics(filters)
