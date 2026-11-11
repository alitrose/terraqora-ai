import logging
from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.db.session import get_db
from app.models.user import FarmerProfile, User
from app.schemas.profile import FarmerProfileOut, FarmerProfileUpdate

logger = logging.getLogger("terraqora.profile")
router = APIRouter(prefix="/profile", tags=["Farmer Profile"])


def _get_or_create_profile(db: Session, user: User) -> FarmerProfile:
    profile = db.scalar(select(FarmerProfile).where(FarmerProfile.user_id == user.id))
    if profile is None:
        profile = FarmerProfile(user_id=user.id, preferred_units="metric")
        db.add(profile)
        db.commit()
        db.refresh(profile)
    return profile


def _serialize_profile(profile: FarmerProfile, user: User) -> FarmerProfileOut:
    return FarmerProfileOut(
        id=profile.id,
        user_id=profile.user_id,
        phone=profile.phone,
        state=profile.state,
        district=profile.district,
        experience_years=profile.experience_years,
        primary_soil_type=profile.primary_soil_type,
        preferred_units=profile.preferred_units,  # type: ignore[arg-type]
        preferred_language=user.preferred_language,  # type: ignore[arg-type]
    )


@router.get("", response_model=FarmerProfileOut)
def get_my_profile(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> FarmerProfileOut:
    profile = _get_or_create_profile(db, current_user)
    return _serialize_profile(profile, current_user)


@router.put("", response_model=FarmerProfileOut)
def update_my_profile(
    payload: FarmerProfileUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> FarmerProfileOut:
    profile = _get_or_create_profile(db, current_user)
    updates = payload.model_dump(exclude_unset=True)

    preferred_language = updates.pop("preferred_language", None)
    if preferred_language is not None:
        current_user.preferred_language = preferred_language

    for field, value in updates.items():
        setattr(profile, field, value)

    db.commit()
    db.refresh(profile)
    db.refresh(current_user)
    logger.info("Updated farmer profile user_id=%s", current_user.id)
    return _serialize_profile(profile, current_user)
