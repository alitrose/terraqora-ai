from datetime import datetime, timezone
import logging
from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.core.rate_limit import limiter
from app.core.security import create_access_token, hash_password, verify_password
from app.db.session import get_db
from app.models.user import FarmerProfile, User
from app.schemas.auth import AuthResponse, LoginRequest, RegisterRequest, UserOut

logger = logging.getLogger("terraqora.auth")
router = APIRouter(prefix="/auth", tags=["Authentication"])


@router.post("/register", response_model=AuthResponse, status_code=status.HTTP_201_CREATED)
@limiter.limit("20/minute")
def register_user(
    request: Request,
    payload: RegisterRequest,
    db: Session = Depends(get_db),
) -> AuthResponse:
    normalized_email = payload.email.strip().lower()
    existing = db.scalar(select(User).where(User.email == normalized_email))
    if existing is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="An account with this email address already exists.",
        )

    now = datetime.now(timezone.utc)
    user = User(
        email=normalized_email,
        hashed_password=hash_password(payload.password),
        full_name=payload.full_name,
        role="farmer",  # Self-registration is strictly scoped to farmer role
        preferred_language=payload.preferred_language,
        is_active=True,
        last_login_at=now,
    )
    db.add(user)
    try:
        db.flush()
        profile = FarmerProfile(
            user_id=user.id,
            state=payload.state.strip() if payload.state and payload.state.strip() else None,
            preferred_units="metric",
        )
        db.add(profile)
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="An account with this email address already exists.",
        ) from exc

    db.refresh(user)
    token = create_access_token(subject=str(user.id), role=user.role)
    logger.info("Registered new farmer user_id=%s", user.id)
    return AuthResponse(access_token=token, token_type="bearer", user=UserOut.model_validate(user))


@router.post("/login", response_model=AuthResponse)
@limiter.limit("30/minute")
def login_user(
    request: Request,
    payload: LoginRequest,
    db: Session = Depends(get_db),
) -> AuthResponse:
    normalized_email = payload.email.strip().lower()
    user = db.scalar(select(User).where(User.email == normalized_email))
    if user is None or not verify_password(payload.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email address or password.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="This account has been deactivated by an administrator.",
        )

    user.last_login_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(user)

    token = create_access_token(subject=str(user.id), role=user.role)
    logger.info("Authenticated user_id=%s role=%s", user.id, user.role)
    return AuthResponse(access_token=token, token_type="bearer", user=UserOut.model_validate(user))


@router.get("/me", response_model=UserOut)
def get_authenticated_user(current_user: User = Depends(get_current_user)) -> UserOut:
    return UserOut.model_validate(current_user)
