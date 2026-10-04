from datetime import timedelta
from decimal import Decimal
from uuid import UUID

from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.models.citizen_report import CitizenReport
from app.models.verification_result import VerificationResult
from app.models.weather_observation import WeatherObservation
from app.models.weather_event import WeatherEvent


VERIFICATION_TIME_WINDOW = timedelta(hours=1)


def calculate_credibility(
    report,
    observations,
    events,
):
    score = Decimal("0.00")
    reasons = []

    report_time = report.reported_at

    # ---------------------------------------------------------
    # Check supporting weather observations
    # ---------------------------------------------------------
    matching_observations = [
        observation
        for observation in observations
        if (
            observation.location_id == report.location_id
            and abs(observation.observed_at - report_time)
            <= VERIFICATION_TIME_WINDOW
        )
    ]

    if matching_observations:
        score += Decimal("0.40")
        reasons.append(
            "Supporting weather observations found within the time window."
        )

    # ---------------------------------------------------------
    # Check matching weather events
    # ---------------------------------------------------------
    matching_events = [
        event
        for event in events
        if (
            event.location_id == report.location_id
            and event.event_type == report.event_type
            and abs(event.start_time - report_time)
            <= VERIFICATION_TIME_WINDOW
        )
    ]

    if matching_events:
        score += Decimal("0.40")
        reasons.append(
            "Matching weather event found within the time window."
        )

    # ---------------------------------------------------------
    # Check report description
    # ---------------------------------------------------------
    if report.description and len(report.description.strip()) >= 10:
        score += Decimal("0.10")
        reasons.append(
            "Report contains a meaningful description."
        )

    # ---------------------------------------------------------
    # Check image evidence
    # ---------------------------------------------------------
    if report.image_url:
        score += Decimal("0.10")
        reasons.append(
            "Report includes image evidence."
        )

    # ---------------------------------------------------------
    # Keep score between 0 and 1
    # ---------------------------------------------------------
    score = min(score, Decimal("1.00"))

    # ---------------------------------------------------------
    # Determine verification status
    # ---------------------------------------------------------
    if score >= Decimal("0.70"):
        status = "likely_valid"
    elif score >= Decimal("0.40"):
        status = "uncertain"
    else:
        status = "likely_misleading"

    # ---------------------------------------------------------
    # Build explanation
    # ---------------------------------------------------------
    reason = (
        " ".join(reasons)
        if reasons
        else "Insufficient supporting evidence."
    )

    return score, status, reason


def verify_citizen_report(
    db: Session,
    report_id: UUID,
) -> VerificationResult:

    # ---------------------------------------------------------
    # Find citizen report
    # ---------------------------------------------------------
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

    # ---------------------------------------------------------
    # Check whether verification already exists
    # ---------------------------------------------------------
    existing_result = (
        db.query(VerificationResult)
        .filter(
            VerificationResult.report_id == report_id
        )
        .first()
    )

    # ---------------------------------------------------------
    # If verification already exists:
    # synchronize citizen report status
    # ---------------------------------------------------------
    if existing_result is not None:

        if existing_result.verification_status == "likely_valid":
            report.status = "verified"

        elif (
            existing_result.verification_status
            == "likely_misleading"
        ):
            report.status = "suspicious"

        else:
            report.status = "pending"

        db.commit()

        return existing_result

    # ---------------------------------------------------------
    # Define verification time window
    # ---------------------------------------------------------
    time_window = VERIFICATION_TIME_WINDOW

    # ---------------------------------------------------------
    # Find weather observations near the report
    # ---------------------------------------------------------
    observations = (
        db.query(WeatherObservation)
        .filter(
            WeatherObservation.location_id
            == report.location_id,
            WeatherObservation.observed_at
            >= report.reported_at - time_window,
            WeatherObservation.observed_at
            <= report.reported_at + time_window,
        )
        .all()
    )

    # ---------------------------------------------------------
    # Find weather events near the report
    # ---------------------------------------------------------
    events = (
        db.query(WeatherEvent)
        .filter(
            WeatherEvent.location_id
            == report.location_id,
            WeatherEvent.start_time
            >= report.reported_at - time_window,
            WeatherEvent.start_time
            <= report.reported_at + time_window,
        )
        .all()
    )

    # ---------------------------------------------------------
    # Calculate credibility
    # ---------------------------------------------------------
    score, status, reason = calculate_credibility(
        report,
        observations,
        events,
    )

    # ---------------------------------------------------------
    # Store supporting evidence information
    # ---------------------------------------------------------
    supporting_observations = {
        "observation_count": len(observations),
        "event_count": len(events),
    }

    # ---------------------------------------------------------
    # Create verification result
    # ---------------------------------------------------------
    verification_result = VerificationResult(
        report_id=report.id,
        credibility_score=score,
        verification_status=status,
        supporting_observations=supporting_observations,
        verification_reason=reason,
        model_version="rule-based-v1",
    )

    # ---------------------------------------------------------
    # Synchronize citizen report status
    # ---------------------------------------------------------
    if status == "likely_valid":
        report.status = "verified"

    elif status == "likely_misleading":
        report.status = "suspicious"

    else:
        report.status = "pending"

    # ---------------------------------------------------------
    # Save verification result
    # ---------------------------------------------------------
    db.add(verification_result)

    db.commit()

    db.refresh(verification_result)

    return verification_result