import logging
import uuid
from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.db.session import get_db
from app.models.farm import Farm
from app.models.user import User
from app.schemas.farm import FarmCreate, FarmOut, FarmUpdate

logger = logging.getLogger("terraqora.farms")
router = APIRouter(prefix="/farms", tags=["Farm Plots"])


def _get_accessible_farm(db: Session, farm_id: uuid.UUID, current_user: User) -> Farm:
    farm = db.get(Farm, farm_id)
    if farm is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Farm plot not found.",
        )
    if farm.user_id != current_user.id and current_user.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You do not have permission to access this farm plot.",
        )
    return farm


@router.get("", response_model=list[FarmOut])
def list_my_farms(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> list[FarmOut]:
    farms = db.scalars(
        select(Farm)
        .where(Farm.user_id == current_user.id)
        .order_by(Farm.created_at.desc())
    ).all()
    return [FarmOut.model_validate(f) for f in farms]


@router.post("", response_model=FarmOut, status_code=status.HTTP_201_CREATED)
def create_farm(
    payload: FarmCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> FarmOut:
    farm = Farm(
        user_id=current_user.id,
        **payload.model_dump(),
    )
    db.add(farm)
    db.commit()
    db.refresh(farm)
    logger.info("Created farm_id=%s user_id=%s", farm.id, current_user.id)
    return FarmOut.model_validate(farm)


@router.get("/{farm_id}", response_model=FarmOut)
def get_farm(
    farm_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> FarmOut:
    farm = _get_accessible_farm(db, farm_id, current_user)
    return FarmOut.model_validate(farm)


@router.put("/{farm_id}", response_model=FarmOut)
@router.patch("/{farm_id}", response_model=FarmOut)
def update_farm(
    farm_id: uuid.UUID,
    payload: FarmUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> FarmOut:
    farm = _get_accessible_farm(db, farm_id, current_user)
    updates = payload.model_dump(exclude_unset=True)
    for field, value in updates.items():
        setattr(farm, field, value)

    db.commit()
    db.refresh(farm)
    logger.info("Updated farm_id=%s user_id=%s", farm.id, current_user.id)
    return FarmOut.model_validate(farm)


@router.delete("/{farm_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_farm(
    farm_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> Response:
    farm = _get_accessible_farm(db, farm_id, current_user)
    db.delete(farm)
    db.commit()
    logger.info("Deleted farm_id=%s user_id=%s", farm_id, current_user.id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
