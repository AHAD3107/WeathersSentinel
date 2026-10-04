from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.database import get_db
from app.schemas.citizen_report import (
    CitizenReportCreate,
    CitizenReportListResponse,
    CitizenReportResponse,
)
from app.services.citizen_report_service import (
    create_citizen_report,
    get_citizen_report,
    get_citizen_reports,
)


router = APIRouter(
    prefix="/api/v1/citizen-reports",
    tags=["Citizen Reports"],
)


@router.post(
    "/",
    response_model=CitizenReportResponse,
)
def create_report(
    data: CitizenReportCreate,
    db: Session = Depends(get_db),
):
    return create_citizen_report(db, data)


@router.get(
    "/",
    response_model=CitizenReportListResponse,
)
def list_reports(
    user_id: UUID | None = Query(default=None),
    location_id: UUID | None = Query(default=None),
    event_type: str | None = Query(default=None),
    status: str | None = Query(default=None),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    db: Session = Depends(get_db),
):
    reports, total = get_citizen_reports(
        db=db,
        user_id=user_id,
        location_id=location_id,
        event_type=event_type,
        status=status,
        page=page,
        page_size=page_size,
    )

    return {
        "items": reports,
        "total": total,
        "page": page,
        "page_size": page_size,
    }


@router.get(
    "/{report_id}",
    response_model=CitizenReportResponse,
)
def get_report(
    report_id: UUID,
    db: Session = Depends(get_db),
):
    return get_citizen_report(db, report_id)