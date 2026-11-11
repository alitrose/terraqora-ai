from fastapi import APIRouter, Depends, Query, Request, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.core.config import get_settings
from app.core.rate_limit import limiter
from app.db.session import get_db
from app.models.user import User
from app.schemas.predictions import CropYieldRequest, CropYieldResponse
from app.services.crop_yield_service import list_yield_history, predict_crop_yield

settings = get_settings()
router = APIRouter(prefix="/predictions", tags=["ML Predictions"])


@router.post(
    "/yield",
    response_model=CropYieldResponse,
    status_code=status.HTTP_200_OK,
)
@limiter.limit(settings.RATE_LIMIT_AI)
def run_crop_yield_prediction(
    request: Request,
    payload: CropYieldRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> CropYieldResponse:
    return predict_crop_yield(db=db, current_user=current_user, payload=payload)


@router.get(
    "/yield/history",
    response_model=list[CropYieldResponse],
    status_code=status.HTTP_200_OK,
)
def get_crop_yield_history(
    limit: int = Query(default=10, ge=1, le=50),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> list[CropYieldResponse]:
    return list_yield_history(db=db, current_user=current_user, limit=limit)
