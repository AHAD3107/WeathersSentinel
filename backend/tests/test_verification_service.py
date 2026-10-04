from datetime import datetime, timedelta
from decimal import Decimal
from types import SimpleNamespace

from app.services.verification_service import calculate_credibility


REPORT_TIME = datetime(2026, 10, 2, 10, 0, 0)


def create_report(
    event_type="rainfall",
    description="Heavy rainfall observed here",
    image_url=None,
):
    return SimpleNamespace(
        location_id="location-1",
        event_type=event_type,
        description=description,
        image_url=image_url,
        reported_at=REPORT_TIME,
    )


def test_no_supporting_evidence():
    report = create_report()

    score, status, reason = calculate_credibility(
        report=report,
        observations=[],
        events=[],
    )

    assert score == Decimal("0.10")
    assert status == "likely_misleading"


def test_observation_within_time_window():
    report = create_report()

    observation = SimpleNamespace(
        location_id="location-1",
        observed_at=REPORT_TIME + timedelta(minutes=30),
    )

    score, status, reason = calculate_credibility(
        report=report,
        observations=[observation],
        events=[],
    )

    assert score == Decimal("0.50")
    assert status == "uncertain"


def test_observation_outside_time_window():
    report = create_report()

    observation = SimpleNamespace(
        location_id="location-1",
        observed_at=REPORT_TIME + timedelta(hours=3),
    )

    score, status, reason = calculate_credibility(
        report=report,
        observations=[observation],
        events=[],
    )

    assert score == Decimal("0.10")
    assert status == "likely_misleading"


def test_event_within_time_window():
    report = create_report()

    event = SimpleNamespace(
        location_id="location-1",
        event_type="rainfall",
        start_time=REPORT_TIME - timedelta(minutes=30),
    )

    score, status, reason = calculate_credibility(
        report=report,
        observations=[],
        events=[event],
    )

    assert score == Decimal("0.50")
    assert status == "uncertain"


def test_event_outside_time_window():
    report = create_report()

    event = SimpleNamespace(
        location_id="location-1",
        event_type="rainfall",
        start_time=REPORT_TIME + timedelta(hours=3),
    )

    score, status, reason = calculate_credibility(
        report=report,
        observations=[],
        events=[event],
    )

    assert score == Decimal("0.10")
    assert status == "likely_misleading"


def test_matching_observation_and_event():
    report = create_report()

    observation = SimpleNamespace(
        location_id="location-1",
        observed_at=REPORT_TIME + timedelta(minutes=20),
    )

    event = SimpleNamespace(
        location_id="location-1",
        event_type="rainfall",
        start_time=REPORT_TIME - timedelta(minutes=20),
    )

    score, status, reason = calculate_credibility(
        report=report,
        observations=[observation],
        events=[event],
    )

    assert score == Decimal("0.90")
    assert status == "likely_valid"


def test_complete_evidence():
    report = create_report(
        description="Heavy rainfall observed here with flooding nearby",
        image_url="https://example.com/weather.jpg",
    )

    observation = SimpleNamespace(
        location_id="location-1",
        observed_at=REPORT_TIME,
    )

    event = SimpleNamespace(
        location_id="location-1",
        event_type="rainfall",
        start_time=REPORT_TIME,
    )

    score, status, reason = calculate_credibility(
        report=report,
        observations=[observation],
        events=[event],
    )

    assert score == Decimal("1.00")
    assert status == "likely_valid"