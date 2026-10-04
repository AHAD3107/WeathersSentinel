from uuid import UUID

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database import get_db
from app.schemas.verification_result import VerificationResultResponse
from app.services.verification_service import verify_citizen_report


router = APIRouter(
    prefix="/api/v1/citizen-reports",
    tags=["Verification"],
)


@router.post(
    "/{report_id}/verify",
    response_model=VerificationResultResponse,
)
def verify_report(
    report_id: UUID,
    db: Session = Depends(get_db),
):
    return verify_citizen_report(
        db=db,
        report_id=report_id,
    )