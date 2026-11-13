from __future__ import annotations

import io
import uuid
from fastapi import APIRouter, Depends, Query, Request
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.core.config import get_settings
from app.core.rate_limit import limiter
from app.db.session import get_db
from app.models.user import User
from app.schemas.reports import GeneratedReportResponse, ReportCreateRequest
from app.services import report_service

settings = get_settings()
router = APIRouter(prefix="/reports", tags=["Reports & PDF Export"])


@router.post("", response_model=GeneratedReportResponse, status_code=201)
@router.post("/generate", response_model=GeneratedReportResponse, status_code=201)
@limiter.limit(settings.RATE_LIMIT_DEFAULT)
def generate_report(
    request: Request,
    payload: ReportCreateRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> GeneratedReportResponse:
    _ = request
    return report_service.create_report(db, current_user, payload)


@router.get("", response_model=list[GeneratedReportResponse])
def list_user_reports(
    limit: int = Query(default=50, ge=1, le=100),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> list[GeneratedReportResponse]:
    return report_service.list_reports(db, current_user, limit=limit)


@router.get("/{report_id}", response_model=GeneratedReportResponse)
def get_report_details(
    report_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> GeneratedReportResponse:
    report = report_service.get_report(db, current_user, report_id)
    farm_name = report.farm.name if report.farm else None
    return report_service._format_report_response(report, farm_name=farm_name)


@router.get("/{report_id}/download")
@router.get("/{report_id}/pdf")
def download_report_pdf(
    report_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> StreamingResponse:
    pdf_bytes, filename = report_service.get_report_pdf_bytes(
        db, current_user, report_id
    )
    return StreamingResponse(
        io.BytesIO(pdf_bytes),
        media_type="application/pdf",
        headers={
            "Content-Disposition": f'attachment; filename="{filename}"',
            "Content-Length": str(len(pdf_bytes)),
        },
    )
