from decimal import Decimal
from types import SimpleNamespace

from app.services.event_detection_service import detect_events


def test_heavy_rainfall_detection():
    observation = SimpleNamespace(
        rainfall=Decimal("60"),
        temperature=Decimal("30"),
        wind_speed=Decimal("20"),
    )

    events = detect_events(observation)

    assert len(events) == 1
    assert events[0]["event_type"] == "rainfall"
    assert events[0]["severity"] == "high"


def test_heatwave_detection():
    observation = SimpleNamespace(
        rainfall=Decimal("5"),
        temperature=Decimal("42"),
        wind_speed=Decimal("20"),
    )

    events = detect_events(observation)

    assert len(events) == 1
    assert events[0]["event_type"] == "heatwave"
    assert events[0]["severity"] == "high"


def test_strong_wind_detection():
    observation = SimpleNamespace(
        rainfall=Decimal("5"),
        temperature=Decimal("30"),
        wind_speed=Decimal("60"),
    )

    events = detect_events(observation)

    assert len(events) == 1
    assert events[0]["event_type"] == "strong_wind"
    assert events[0]["severity"] == "high"


def test_no_event():
    observation = SimpleNamespace(
        rainfall=Decimal("10"),
        temperature=Decimal("30"),
        wind_speed=Decimal("20"),
    )

    events = detect_events(observation)

    assert events == []


def test_multiple_events():
    observation = SimpleNamespace(
        rainfall=Decimal("70"),
        temperature=Decimal("42"),
        wind_speed=Decimal("60"),
    )

    events = detect_events(observation)

    assert len(events) == 3

def test_rainfall_threshold_boundary():
    observation = SimpleNamespace(
        rainfall=Decimal("50"),
        temperature=Decimal("30"),
        wind_speed=Decimal("20"),
    )

    events = detect_events(observation)

    assert len(events) == 1
    assert events[0]["event_type"] == "rainfall"


def test_temperature_threshold_boundary():
    observation = SimpleNamespace(
        rainfall=Decimal("5"),
        temperature=Decimal("40"),
        wind_speed=Decimal("20"),
    )

    events = detect_events(observation)

    assert len(events) == 1
    assert events[0]["event_type"] == "heatwave"


def test_wind_threshold_boundary():
    observation = SimpleNamespace(
        rainfall=Decimal("5"),
        temperature=Decimal("30"),
        wind_speed=Decimal("50"),
    )

    events = detect_events(observation)

    assert len(events) == 1
    assert events[0]["event_type"] == "strong_wind"


def test_missing_weather_values():
    observation = SimpleNamespace(
        rainfall=None,
        temperature=None,
        wind_speed=None,
    )

    events = detect_events(observation)

    assert events == []


def test_confidence_score_is_bounded():
    observation = SimpleNamespace(
        rainfall=Decimal("500"),
        temperature=Decimal("80"),
        wind_speed=Decimal("200"),
    )

    events = detect_events(observation)

    assert len(events) == 3

    for event in events:
        assert Decimal("0") <= event["confidence_score"] <= Decimal("0.99")