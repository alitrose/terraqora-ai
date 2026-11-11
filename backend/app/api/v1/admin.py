import logging
import uuid
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.api.deps import require_roles
from app.db.session import get_db
from app.models.farm import Farm
from app.models.modules import ChatSession, CropPrediction, DiseaseDetection
from app.models.user import User
from app.schemas.admin import (
    AdminModelStatusItem,
    AdminOverviewResponse,
    AdminUserItem,
    AdminUserUpdate,
)

logger = logging.getLogger("terraqora.admin")
router = APIRouter(prefix="/admin", tags=["Administration"])


def _fetch_user_directory(db: Session) -> list[AdminUserItem]:
    farm_counts_sq = (
        select(Farm.user_id, func.count(Farm.id).label("farms_count"))
        .group_by(Farm.user_id)
        .subquery()
    )
    pred_counts_sq = (
        select(
            CropPrediction.user_id,
            func.count(CropPrediction.id).label("predictions_count"),
        )
        .group_by(CropPrediction.user_id)
        .subquery()
    )

    rows = db.execute(
        select(
            User,
            func.coalesce(farm_counts_sq.c.farms_count, 0).label("farms_count"),
            func.coalesce(pred_counts_sq.c.predictions_count, 0).label(
                "predictions_count"
            ),
        )
        .outerjoin(farm_counts_sq, User.id == farm_counts_sq.c.user_id)
        .outerjoin(pred_counts_sq, User.id == pred_counts_sq.c.user_id)
        .order_by(User.created_at.desc())
    ).all()

    return [
        AdminUserItem(
            id=user.id,
            full_name=user.full_name,
            email=user.email,
            role=user.role,  # type: ignore[arg-type]
            preferred_language=user.preferred_language,  # type: ignore[arg-type]
            is_active=user.is_active,
            farms_count=int(farms_count),
            predictions_count=int(predictions_count),
            created_at=user.created_at,
        )
        for user, farms_count, predictions_count in rows
    ]


@router.get("/overview", response_model=AdminOverviewResponse)
def get_admin_overview(
    current_admin: User = Depends(require_roles("admin")),
    db: Session = Depends(get_db),
) -> AdminOverviewResponse:
    total_users = db.scalar(select(func.count(User.id))) or 0
    active_farms = db.scalar(select(func.count(Farm.id))) or 0
    total_predictions = db.scalar(select(func.count(CropPrediction.id))) or 0
    total_disease_scans = db.scalar(select(func.count(DiseaseDetection.id))) or 0
    total_ai_chats = db.scalar(select(func.count(ChatSession.id))) or 0

    models = [
        AdminModelStatusItem(
            module="Crop Yield Prediction",
            algorithm="XGBoost / Random Forest (Leak-Free Pipeline)",
            status="Phase 5 Scheduled",
            metric_label="Chronological R²",
            metric_value="Pending Phase 5 Training",
            artifact_size="< 15 MB target",
        ),
        AdminModelStatusItem(
            module="Plant Disease Vision",
            algorithm="MobileNetV2 Transfer Learning (TensorFlow/Keras + TFLite)",
            status="Phase 7 Scheduled",
            metric_label="Validation F1",
            metric_value="Pending Phase 7 Training",
            artifact_size="< 10 MB target",
        ),
        AdminModelStatusItem(
            module="Crop Recommendation",
            algorithm="Random Forest / Light Pipeline (22 Crops)",
            status="Phase 5 Scheduled",
            metric_label="5-Fold Accuracy",
            metric_value="Pending Phase 5 Training",
            artifact_size="< 5 MB target",
        ),
        AdminModelStatusItem(
            module="Fertilizer Recommendation",
            algorithm="Gradient Boosted Classifier + Agronomic Guardrails",
            status="Phase 5 Scheduled",
            metric_label="Stratified F1",
            metric_value="Pending Phase 5 Training",
            artifact_size="< 4 MB target",
        ),
    ]

    logger.info("Admin overview queried by admin_id=%s", current_admin.id)
    return AdminOverviewResponse(
        total_users=int(total_users),
        active_farms=int(active_farms),
        total_predictions=int(total_predictions),
        total_disease_scans=int(total_disease_scans),
        total_ai_chats=int(total_ai_chats),
        models=models,
        users=_fetch_user_directory(db),
        source_mode="live_api",
    )


@router.get("/users", response_model=list[AdminUserItem])
def list_platform_users(
    _current_admin: User = Depends(require_roles("admin")),
    db: Session = Depends(get_db),
) -> list[AdminUserItem]:
    return _fetch_user_directory(db)


@router.patch("/users/{user_id}", response_model=AdminUserItem)
def update_user_account_access(
    user_id: uuid.UUID,
    payload: AdminUserUpdate,
    current_admin: User = Depends(require_roles("admin")),
    db: Session = Depends(get_db),
) -> AdminUserItem:
    target = db.get(User, user_id)
    if target is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Target user not found.",
        )

    updates = payload.model_dump(exclude_unset=True)
    if target.id == current_admin.id:
        if updates.get("is_active") is False or (
            "role" in updates and updates["role"] != "admin"
        ):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Administrators cannot deactivate or demote their own active account.",
            )

    for field, value in updates.items():
        setattr(target, field, value)

    db.commit()
    db.refresh(target)

    farms_count = db.scalar(select(func.count(Farm.id)).where(Farm.user_id == target.id)) or 0
    preds_count = (
        db.scalar(
            select(func.count(CropPrediction.id)).where(CropPrediction.user_id == target.id)
        )
        or 0
    )

    logger.info(
        "Admin user_id=%s updated access for target_user_id=%s",
        current_admin.id,
        target.id,
    )
    return AdminUserItem(
        id=target.id,
        full_name=target.full_name,
        email=target.email,
        role=target.role,  # type: ignore[arg-type]
        preferred_language=target.preferred_language,  # type: ignore[arg-type]
        is_active=target.is_active,
        farms_count=int(farms_count),
        predictions_count=int(preds_count),
        created_at=target.created_at,
    )
