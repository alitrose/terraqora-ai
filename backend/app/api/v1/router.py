from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.api.v1 import admin, auth, farms, profile
from app.db.session import get_db

api_v1_router = APIRouter()


@api_v1_router.get("/health", tags=["Health"])
def api_health_check(db: Session = Depends(get_db)) -> dict[str, str]:
    try:
        db.execute(text("SELECT 1"))
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Database connectivity check failed.",
        ) from exc

    return {
        "status": "ok",
        "service": "TerraQora AI API",
        "version": "0.1.0",
        "database": "connected",
    }


api_v1_router.include_router(auth.router)
api_v1_router.include_router(profile.router)
api_v1_router.include_router(farms.router)
api_v1_router.include_router(admin.router)
