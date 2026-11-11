from fastapi import APIRouter, Depends, Query, Request, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.core.config import get_settings
from app.core.rate_limit import limiter
from app.db.session import get_db
from app.models.user import User
from app.schemas.recommendations import (
    CropRecommendationRequest,
    CropRecommendationResponse,
    FertilizerRequest,
    FertilizerResponse,
)
from app.services.crop_rec_service import (
    list_crop_recommendation_history,
    recommend_crop,
)
from app.services.fertilizer_service import (
    list_fertilizer_history,
    recommend_fertilizer,
)

settings = get_settings()
router = APIRouter(prefix="/recommendations", tags=["Recommendations (ML)"])


@router.post(
    "/crop",
    response_model=CropRecommendationResponse,
    status_code=status.HTTP_200_OK,
)
@limiter.limit(settings.RATE_LIMIT_AI)
def run_crop_recommendation(
    request: Request,
    payload: CropRecommendationRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> CropRecommendationResponse:
    return recommend_crop(db=db, current_user=current_user, payload=payload)


@router.get(
    "/crop/history",
    response_model=list[CropRecommendationResponse],
    status_code=status.HTTP_200_OK,
)
def get_crop_recommendation_history(
    limit: int = Query(default=10, ge=1, le=50),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> list[CropRecommendationResponse]:
    return list_crop_recommendation_history(db=db, current_user=current_user, limit=limit)


@router.post(
    "/fertilizer",
    response_model=FertilizerResponse,
    status_code=status.HTTP_200_OK,
)
@limiter.limit(settings.RATE_LIMIT_AI)
def run_fertilizer_recommendation(
    request: Request,
    payload: FertilizerRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> FertilizerResponse:
    return recommend_fertilizer(db=db, current_user=current_user, payload=payload)


@router.get(
    "/fertilizer/history",
    response_model=list[FertilizerResponse],
    status_code=status.HTTP_200_OK,
)
def get_fertilizer_recommendation_history(
    limit: int = Query(default=10, ge=1, le=50),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> list[FertilizerResponse]:
    return list_fertilizer_history(db=db, current_user=current_user, limit=limit)
