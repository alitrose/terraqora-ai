from fastapi import APIRouter, Depends, Query, Request
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.core.config import get_settings
from app.core.rate_limit import limiter
from app.db.session import get_db
from app.models.user import User
from app.schemas.weather import WeatherIrrigationRequest, WeatherIrrigationResponse
from app.services import weather_service

settings = get_settings()
router = APIRouter(prefix="/weather", tags=["Weather & Irrigation"])


@router.post("/irrigation", response_model=WeatherIrrigationResponse)
@limiter.limit(settings.RATE_LIMIT_DEFAULT)
def get_weather_irrigation_advisory(
    request: Request,
    payload: WeatherIrrigationRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> WeatherIrrigationResponse:
    _ = request
    return weather_service.compute_weather_irrigation_advisory(
        db, current_user, payload
    )


@router.get("/irrigation/history", response_model=list[WeatherIrrigationResponse])
def get_weather_irrigation_history(
    limit: int = Query(default=10, ge=1, le=50),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> list[WeatherIrrigationResponse]:
    return weather_service.list_irrigation_history(db, current_user, limit=limit)
