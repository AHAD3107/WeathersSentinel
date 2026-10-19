"""Automated tests for weather event coordinate resolution and geospatial integrity.

Verifies:
1. Valid coordinates from direct payload or linked location telemetry.
2. Missing coordinates return None and are never fabricated.
3. Invalid coordinate ranges (lat outside [-90, 90], lon outside [-180, 180], non-numeric).
4. Unresolved location IDs omit map markers and produce clear explanations.
5. Strict prevention of arbitrary/default fallback positions (e.g., Pune DEFAULT_CENTER).
6. Retention of unmapped events in event feeds with full metadata.
"""

import math
import pytest
from api.client import (
    get_event_location_resolution,
    resolve_event_coordinates,
)

PUNE_DEFAULT_CENTER = (18.5204, 73.8567)


def test_event_with_valid_direct_coordinates():
    """Event with direct payload coordinates resolves correctly."""
    event = {
        "id": "ev-1",
        "location_id": "loc-direct",
        "event_type": "rainfall",
        "latitude": 18.5237,
        "longitude": 73.8688,
    }
    coords = resolve_event_coordinates(event)
    assert coords == (18.5237, 73.8688)

    res = get_event_location_resolution(event)
    assert res["is_mappable"] is True
    assert res["coordinates"] == (18.5237, 73.8688)
    assert res["source_type"] == "event_payload"
    assert "Direct GPS coordinates" in res["reason"]


def test_event_with_valid_raw_data_coordinates():
    """Event with coordinates in raw_data resolves correctly."""
    event = {
        "id": "ev-2",
        "location_id": "loc-raw",
        "event_type": "thunderstorm",
        "raw_data": {
            "latitude": 19.0760,
            "longitude": 72.8777,
        },
    }
    coords = resolve_event_coordinates(event)
    assert coords == (19.0760, 72.8777)

    res = get_event_location_resolution(event)
    assert res["is_mappable"] is True
    assert res["coordinates"] == (19.0760, 72.8777)
    assert res["source_type"] == "event_payload"


def test_event_with_verified_linked_location_telemetry():
    """Event with location_id matching verified telemetry resolves to actual linked location."""
    loc_id = "6de4641d-3940-4b87-8505-34f244bc18b9"
    verified_location_map = {
        loc_id: (18.5237, 73.8688),
    }

    event = {
        "id": "ev-3",
        "location_id": loc_id,
        "event_type": "heatwave",
        "severity": "high",
    }

    coords = resolve_event_coordinates(event, verified_location_map)
    assert coords == (18.5237, 73.8688)

    res = get_event_location_resolution(event, verified_location_map)
    assert res["is_mappable"] is True
    assert res["coordinates"] == (18.5237, 73.8688)
    assert res["source_type"] == "linked_telemetry"
    assert "verified from linked location telemetry" in res["reason"]


def test_event_with_unresolved_location_id_returns_none():
    """Event referencing an unknown location_id must return None, not a fallback."""
    unresolved_loc_id = "2e9ee57c-42d5-46ef-95bb-1a9fb4b74285"
    verified_location_map = {
        "6de4641d-3940-4b87-8505-34f244bc18b9": (18.5237, 73.8688),
    }

    event = {
        "id": "ev-4",
        "location_id": unresolved_loc_id,
        "event_type": "rainfall",
        "severity": "high",
    }

    coords = resolve_event_coordinates(event, verified_location_map)
    assert coords is None

    res = get_event_location_resolution(event, verified_location_map)
    assert res["is_mappable"] is False
    assert res["coordinates"] is None
    assert res["source_type"] == "unresolved"
    assert unresolved_loc_id in res["reason"]
    assert "lacks verified GPS coordinates" in res["reason"]


def test_strict_prevention_of_fabricated_or_default_positions():
    """CRITICAL: Unresolved events must NEVER fall back to default station coordinates."""
    unresolved_event = {
        "id": "ev-unresolved",
        "location_id": "test-station-without-gps",
        "event_type": "flooding",
        "severity": "extreme",
    }

    # With empty map
    coords = resolve_event_coordinates(unresolved_event, {})
    assert coords is None
    assert coords != PUNE_DEFAULT_CENTER

    # With None map
    coords = resolve_event_coordinates(unresolved_event, None)
    assert coords is None
    assert coords != PUNE_DEFAULT_CENTER

    # With map containing other unrelated locations
    coords = resolve_event_coordinates(
        unresolved_event,
        {"some_other_location_id": PUNE_DEFAULT_CENTER},
    )
    assert coords is None
    assert coords != PUNE_DEFAULT_CENTER

    res = get_event_location_resolution(unresolved_event, {})
    assert res["is_mappable"] is False
    assert res["coordinates"] is None


def test_invalid_coordinate_ranges_rejected():
    """Latitude outside [-90, 90] and longitude outside [-180, 180] must be rejected."""
    # Latitude > 90
    ev1 = {"location_id": "loc-1", "latitude": 90.0001, "longitude": 73.0}
    assert resolve_event_coordinates(ev1) is None
    assert get_event_location_resolution(ev1)["is_mappable"] is False

    # Latitude < -90
    ev2 = {"location_id": "loc-2", "latitude": -90.5, "longitude": 73.0}
    assert resolve_event_coordinates(ev2) is None
    assert get_event_location_resolution(ev2)["is_mappable"] is False

    # Longitude > 180
    ev3 = {"location_id": "loc-3", "latitude": 18.0, "longitude": 180.1}
    assert resolve_event_coordinates(ev3) is None
    assert get_event_location_resolution(ev3)["is_mappable"] is False

    # Longitude < -180
    ev4 = {"location_id": "loc-4", "latitude": 18.0, "longitude": -180.1}
    assert resolve_event_coordinates(ev4) is None
    assert get_event_location_resolution(ev4)["is_mappable"] is False

    # Non-numeric strings
    ev5 = {"location_id": "loc-5", "latitude": "unknown", "longitude": "coords"}
    assert resolve_event_coordinates(ev5) is None
    assert get_event_location_resolution(ev5)["is_mappable"] is False

    # Invalid in linked telemetry map
    invalid_map = {"loc-6": (120.0, 73.0)}
    ev6 = {"location_id": "loc-6"}
    assert resolve_event_coordinates(ev6, invalid_map) is None
    res6 = get_event_location_resolution(ev6, invalid_map)
    assert res6["is_mappable"] is False
    assert res6["source_type"] == "invalid_range"


def test_event_with_no_location_id_or_empty_dict():
    """Event without location_id is handled gracefully without crashing."""
    assert resolve_event_coordinates({}) is None
    assert resolve_event_coordinates(None) is None
    assert resolve_event_coordinates({"location_id": None}) is None
    assert resolve_event_coordinates({"location_id": ""}) is None

    res_empty = get_event_location_resolution({})
    assert res_empty["is_mappable"] is False
    assert res_empty["coordinates"] is None

    res_none = get_event_location_resolution(None)
    assert res_none["is_mappable"] is False


def test_event_feed_retains_unmapped_events_with_explanation():
    """Verify that unmapped events are preserved in feeds rather than dropped."""
    known_map = {"loc-pune": (18.52, 73.85)}

    events = [
        {"id": "ev-mapped", "location_id": "loc-pune", "event_type": "rainfall", "severity": "high"},
        {"id": "ev-unmapped", "location_id": "loc-unknown", "event_type": "heatwave", "severity": "medium"},
    ]

    feed_items = []
    for ev in events:
        res = get_event_location_resolution(ev, known_map)
        feed_items.append({
            "id": ev["id"],
            "event_type": ev["event_type"],
            "severity": ev["severity"],
            "is_mappable": res["is_mappable"],
            "coordinates": res["coordinates"],
            "reason": res["reason"],
        })

    # Total events preserved
    assert len(feed_items) == 2

    # First event mapped
    assert feed_items[0]["is_mappable"] is True
    assert feed_items[0]["coordinates"] == (18.52, 73.85)

    # Second event unmapped, but present in feed with full explanation
    assert feed_items[1]["is_mappable"] is False
    assert feed_items[1]["coordinates"] is None
    assert "loc-unknown" in feed_items[1]["reason"]
    assert "lacks verified GPS coordinates" in feed_items[1]["reason"]
