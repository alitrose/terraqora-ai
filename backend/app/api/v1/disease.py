import uuid
from fastapi import APIRouter, Depends, File, Form, Query, Request, UploadFile
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.core.config import get_settings
from app.core.rate_limit import limiter
from app.db.session import get_db
from app.models.user import User
from app.schemas.disease import DiseaseDetectionResponse
from app.services import disease_service

settings = get_settings()
router = APIRouter(prefix="/disease", tags=["Plant Disease Detection"])


@router.post("/detect", response_model=DiseaseDetectionResponse)
@limiter.limit(settings.RATE_LIMIT_AI)
async def detect_leaf_disease(
    request: Request,
    file: UploadFile = File(...),
    crop_hint: str | None = Form(default=None),
    farm_id: uuid.UUID | None = Form(default=None),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> DiseaseDetectionResponse:
    _ = request
    image_bytes = await file.read()
    return disease_service.detect_plant_disease(
        db,
        current_user,
        image_bytes=image_bytes,
        filename=file.filename,
        content_type=file.content_type,
        crop_hint=crop_hint,
        farm_id=farm_id,
    )


@router.get("/history", response_model=list[DiseaseDetectionResponse])
def get_disease_detection_history(
    limit: int = Query(default=10, ge=1, le=50),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> list[DiseaseDetectionResponse]:
    return disease_service.list_disease_history(db, current_user, limit=limit)
