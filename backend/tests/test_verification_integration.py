from datetime import datetime, timedelta, timezone
from decimal import Decimal
from uuid import uuid4

from app.database import SessionLocal
from app.models.user import User
from app.models.location import Location
from app.models.citizen_report import CitizenReport
from app.models.weather_observation import WeatherObservation
from app.models.weather_event import WeatherEvent
from app.models.verification_result import VerificationResult
from app.services.verification_service import verify_citizen_report


def test_full_citizen_report_verification():
    db = SessionLocal()

    user = None
    location = None
    report = None
    observation = None
    event = None
    result = None

    try:
        now = datetime.now(timezone.utc)

        # ---------------------------------------------------------
        # Create test user
        # ---------------------------------------------------------
        user = User(
            id=uuid4(),
            name="Verification Test User",
            email=f"verification-{uuid4()}@test.local",
            password_hash="test-password",
            role="citizen",
            is_active=True,
        )

        # ---------------------------------------------------------
        # Create test location
        # ---------------------------------------------------------
        location = Location(
            id=uuid4(),
            name="Test Location",
            district="Test District",
            state="Maharashtra",
            country="India",
            latitude=Decimal("16.700000"),
            longitude=Decimal("74.200000"),
            geometry="SRID=4326;POINT(74.2 16.7)",
        )

        db.add_all([user, location])
        db.flush()

        # ---------------------------------------------------------
        # Create citizen report
        # ---------------------------------------------------------
        report = CitizenReport(
            id=uuid4(),
            user_id=user.id,
            location_id=location.id,
            event_type="rainfall",
            description="Heavy rainfall observed in the area",
            reported_at=now,
            image_url=None,
            status="pending",
        )

        # ---------------------------------------------------------
        # Create matching weather observation
        # ---------------------------------------------------------
        observation = WeatherObservation(
            id=uuid4(),
            location_id=location.id,
            source="test-source",
            observed_at=now + timedelta(minutes=20),
            temperature=Decimal("28.00"),
            humidity=Decimal("90.00"),
            pressure=Decimal("1000.00"),
            rainfall=Decimal("70.00"),
            wind_speed=Decimal("20.00"),
            wind_direction=Decimal("180.00"),
            visibility=Decimal("5.00"),
            weather_condition="heavy rain",
            raw_data={"test": True},
        )

        # ---------------------------------------------------------
        # Create matching weather event
        # ---------------------------------------------------------
        event = WeatherEvent(
            id=uuid4(),
            location_id=location.id,
            event_type="rainfall",
            start_time=now + timedelta(minutes=15),
            end_time=now + timedelta(minutes=20),
            severity="high",
            confidence_score=Decimal("0.90"),
            source="test-source",
        )

        db.add_all([report, observation, event])
        db.commit()

        # ---------------------------------------------------------
        # Run verification engine
        # ---------------------------------------------------------
        result = verify_citizen_report(
            db=db,
            report_id=report.id,
        )

        # ---------------------------------------------------------
        # Verify returned result
        # ---------------------------------------------------------
        assert result is not None
        assert result.report_id == report.id
        assert result.credibility_score == Decimal("0.90")
        assert result.verification_status == "likely_valid"
        assert result.model_version == "rule-based-v1"

        # ---------------------------------------------------------
        # Verify citizen report status was updated
        # ---------------------------------------------------------
        db.refresh(report)

        assert report.status == "verified"

        # ---------------------------------------------------------
        # Verify result was stored in PostgreSQL
        # ---------------------------------------------------------
        stored_result = (
            db.query(VerificationResult)
            .filter(
                VerificationResult.report_id == report.id
            )
            .first()
        )

        assert stored_result is not None
        assert stored_result.id == result.id

    finally:
        # ---------------------------------------------------------
        # Delete verification result first
        # ---------------------------------------------------------
        if result is not None:
            db.delete(result)
            db.flush()

        # ---------------------------------------------------------
        # Delete citizen report
        # ---------------------------------------------------------
        if report is not None:
            db.delete(report)
            db.flush()

        # ---------------------------------------------------------
        # Delete weather observation
        # ---------------------------------------------------------
        if observation is not None:
            db.delete(observation)

        # ---------------------------------------------------------
        # Delete weather event
        # ---------------------------------------------------------
        if event is not None:
            db.delete(event)

        db.flush()

        # ---------------------------------------------------------
        # Delete user
        # ---------------------------------------------------------
        if user is not None:
            db.delete(user)

        db.flush()

        # ---------------------------------------------------------
        # Delete location last
        # ---------------------------------------------------------
        if location is not None:
            db.delete(location)

        db.commit()
        db.close()


def test_existing_verification_synchronizes_report_status():
    db = SessionLocal()

    user = None
    location = None
    report = None
    result = None

    try:
        now = datetime.now(timezone.utc)

        # ---------------------------------------------------------
        # Create test user
        # ---------------------------------------------------------
        user = User(
            id=uuid4(),
            name="Existing Verification Test User",
            email=f"existing-verification-{uuid4()}@test.local",
            password_hash="test-password",
            role="citizen",
            is_active=True,
        )

        # ---------------------------------------------------------
        # Create test location
        # ---------------------------------------------------------
        location = Location(
            id=uuid4(),
            name="Existing Verification Location",
            district="Test District",
            state="Maharashtra",
            country="India",
            latitude=Decimal("16.700000"),
            longitude=Decimal("74.200000"),
            geometry="SRID=4326;POINT(74.2 16.7)",
        )

        db.add_all([user, location])
        db.flush()

        # ---------------------------------------------------------
        # Create citizen report
        # ---------------------------------------------------------
        report = CitizenReport(
            id=uuid4(),
            user_id=user.id,
            location_id=location.id,
            event_type="rainfall",
            description="Potentially misleading rainfall report",
            reported_at=now,
            image_url=None,
            status="pending",
        )

        db.add(report)
        db.flush()

        # ---------------------------------------------------------
        # Create an existing verification result
        # ---------------------------------------------------------
        result = VerificationResult(
            id=uuid4(),
            report_id=report.id,
            credibility_score=Decimal("0.10"),
            verification_status="likely_misleading",
            supporting_observations={
                "observation_count": 0,
                "event_count": 0,
            },
            verification_reason="Insufficient supporting evidence.",
            model_version="rule-based-v1",
        )

        db.add(result)
        db.commit()

        # ---------------------------------------------------------
        # Confirm initial report status
        # ---------------------------------------------------------
        assert report.status == "pending"

        # ---------------------------------------------------------
        # Run verification again
        # Existing result should be reused
        # ---------------------------------------------------------
        returned_result = verify_citizen_report(
            db=db,
            report_id=report.id,
        )

        # ---------------------------------------------------------
        # Verify existing result was returned
        # ---------------------------------------------------------
        assert returned_result is not None
        assert returned_result.id == result.id
        assert returned_result.verification_status == "likely_misleading"
        assert returned_result.credibility_score == Decimal("0.10")

        # ---------------------------------------------------------
        # Verify report status was synchronized
        # ---------------------------------------------------------
        db.refresh(report)

        assert report.status == "suspicious"

    finally:
        # ---------------------------------------------------------
        # Delete verification result
        # ---------------------------------------------------------
        if result is not None:
            db.delete(result)
            db.flush()

        # ---------------------------------------------------------
        # Delete citizen report
        # ---------------------------------------------------------
        if report is not None:
            db.delete(report)
            db.flush()

        # ---------------------------------------------------------
        # Delete user
        # ---------------------------------------------------------
        if user is not None:
            db.delete(user)

        db.flush()

        # ---------------------------------------------------------
        # Delete location
        # ---------------------------------------------------------
        if location is not None:
            db.delete(location)

        db.commit()
        db.close()