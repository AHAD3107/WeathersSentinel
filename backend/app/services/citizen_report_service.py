from uuid import UUID

from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.models.citizen_report import CitizenReport
from app.models.location import Location
from app.models.user import User
from app.schemas.citizen_report import CitizenReportCreate


def create_citizen_report(
    db: Session,
    data: CitizenReportCreate,
) -> CitizenReport:
    # 1. Validate location existence
    location = db.query(Location).filter(Location.id == data.location_id).first()
    if location is None:
        raise HTTPException(
            status_code=400,
            detail=f"Location with ID '{data.location_id}' does not exist.",
        )

    # 2. Resolve or validate user
    user_id = data.user_id
    if user_id is None:
        user = (
            db.query(User)
            .filter(User.is_active == True)
            .order_by(User.created_at.asc())
            .first()
        )
        if user is None:
            user = User(
                name="Citizen Reporter",
                email="citizen@weathersentinel.local",
                password_hash="system-default",
                role="citizen",
                is_active=True,
            )
            db.add(user)
            db.flush()
        user_id = user.id
    else:
        user = db.query(User).filter(User.id == user_id).first()
        if user is None:
            raise HTTPException(
                status_code=400,
                detail=f"User with ID '{user_id}' does not exist.",
            )

    report = CitizenReport(
        user_id=user_id,
        location_id=data.location_id,
        event_type=data.event_type,
        description=data.description,
        reported_at=data.reported_at,
        image_url=data.image_url,
        status="pending",
    )

    db.add(report)
    db.commit()
    db.refresh(report)

    return report


def get_citizen_reports(
    db: Session,
    user_id: UUID | None = None,
    location_id: UUID | None = None,
    event_type: str | None = None,
    status: str | None = None,
    page: int = 1,
    page_size: int = 20,
):
    query = db.query(CitizenReport)

    if user_id is not None:
        query = query.filter(
            CitizenReport.user_id == user_id
        )

    if location_id is not None:
        query = query.filter(
            CitizenReport.location_id == location_id
        )

    if event_type is not None:
        query = query.filter(
            CitizenReport.event_type == event_type.lower()
        )

    if status is not None:
        query = query.filter(
            CitizenReport.status == status.lower()
        )

    total = query.count()

    offset = (page - 1) * page_size

    reports = (
        query
        .order_by(CitizenReport.reported_at.desc())
        .offset(offset)
        .limit(page_size)
        .all()
    )

    return reports, total


def get_citizen_report(
    db: Session,
    report_id: UUID,
) -> CitizenReport:

    report = (
        db.query(CitizenReport)
        .filter(CitizenReport.id == report_id)
        .first()
    )

    if report is None:
        raise HTTPException(
            status_code=404,
            detail="Citizen report not found",
        )

    return report