"""Unit and integration tests for citizen report submission workflow in WeatherSentinel."""

from datetime import datetime, timezone
from unittest.mock import AsyncMock, patch
from uuid import uuid4

import pytest
import httpx

from api.client import (
    ALLOWED_CITIZEN_EVENT_TYPES,
    create_citizen_report,
    format_citizen_report_description,
    get_citizen_reports,
    get_locations,
    validate_citizen_report_submission,
    verify_citizen_report,
)


def test_validate_submission_valid_payload():
    valid_payload = {
        "location_id": str(uuid4()),
        "event_type": "rainfall",
        "reported_at": datetime.now(timezone.utc).isoformat(),
        "description": "Heavy rain observed near the metro station.",
        "measurements": {
            "temperature": 24.5,
            "rainfall": 15.0,
            "humidity": 88.0,
            "wind_speed": 12.0,
        },
    }
    is_valid, error_msg = validate_citizen_report_submission(valid_payload)
    assert is_valid is True
    assert error_msg is None


def test_validate_submission_missing_location():
    payload = {
        "location_id": "",
        "event_type": "rainfall",
        "reported_at": datetime.now(timezone.utc).isoformat(),
        "description": "Rainfall observed without location.",
    }
    is_valid, error_msg = validate_citizen_report_submission(payload)
    assert is_valid is False
    assert "Location / Weather Station is mandatory" in error_msg


def test_validate_submission_missing_event_type():
    payload = {
        "location_id": str(uuid4()),
        "event_type": "",
        "reported_at": datetime.now(timezone.utc).isoformat(),
        "description": "Valid description text here.",
    }
    is_valid, error_msg = validate_citizen_report_submission(payload)
    assert is_valid is False
    assert "Weather condition / event type is mandatory" in error_msg


def test_validate_submission_invalid_event_type():
    payload = {
        "location_id": str(uuid4()),
        "event_type": "tornado_blizzard_storm",
        "reported_at": datetime.now(timezone.utc).isoformat(),
        "description": "Valid description text here.",
    }
    is_valid, error_msg = validate_citizen_report_submission(payload)
    assert is_valid is False
    assert "Invalid event type" in error_msg


def test_validate_submission_missing_timestamp():
    payload = {
        "location_id": str(uuid4()),
        "event_type": "thunderstorm",
        "reported_at": "",
        "description": "Valid description text here.",
    }
    is_valid, error_msg = validate_citizen_report_submission(payload)
    assert is_valid is False
    assert "Observation timestamp is mandatory" in error_msg


def test_validate_submission_description_too_short():
    payload = {
        "location_id": str(uuid4()),
        "event_type": "thunderstorm",
        "reported_at": datetime.now(timezone.utc).isoformat(),
        "description": "Rain",
    }
    is_valid, error_msg = validate_citizen_report_submission(payload)
    assert is_valid is False
    assert "at least 5 characters" in error_msg


def test_validate_submission_invalid_measurements():
    base_payload = {
        "location_id": str(uuid4()),
        "event_type": "rainfall",
        "reported_at": datetime.now(timezone.utc).isoformat(),
        "description": "Heavy rainfall observed.",
    }

    # Temperature too high
    p1 = {**base_payload, "measurements": {"temperature": 120.0}}
    assert validate_citizen_report_submission(p1)[0] is False

    # Negative rainfall
    p2 = {**base_payload, "measurements": {"rainfall": -5.0}}
    assert validate_citizen_report_submission(p2)[0] is False

    # Negative wind speed
    p3 = {**base_payload, "measurements": {"wind_speed": -10.0}}
    assert validate_citizen_report_submission(p3)[0] is False

    # Humidity over 100%
    p4 = {**base_payload, "measurements": {"humidity": 150.0}}
    assert validate_citizen_report_submission(p4)[0] is False


def test_format_citizen_report_description():
    notes = "Waterlogging reported on Senapati Bapat Road."
    measurements = {
        "temperature": 27.2,
        "rainfall": 22.0,
        "humidity": 92.0,
        "wind_speed": 16.5,
    }
    desc = format_citizen_report_description(notes, measurements)
    assert "Waterlogging reported on Senapati Bapat Road." in desc
    assert "Temp: 27.2°C" in desc
    assert "Rain: 22.0 mm" in desc
    assert "Humidity: 92.0%" in desc
    assert "Wind: 16.5 km/h" in desc
    assert len(desc) >= 5


def test_format_citizen_report_description_measurements_only():
    measurements = {"temperature": 25.0, "rainfall": 10.0}
    desc = format_citizen_report_description(None, measurements)
    assert "Temp: 25.0°C" in desc
    assert "Rain: 10.0 mm" in desc
    assert len(desc) >= 5


import asyncio


def test_create_citizen_report_client_call():
    async def run():
        mock_response = {
            "id": str(uuid4()),
            "location_id": str(uuid4()),
            "event_type": "rainfall",
            "description": "Persistent rain across the district.",
            "reported_at": datetime.now(timezone.utc).isoformat(),
            "status": "pending",
            "created_at": datetime.now(timezone.utc).isoformat(),
        }

        with patch("api.client.post_json", new_callable=AsyncMock) as mock_post:
            mock_post.return_value = mock_response

            report_payload = {
                "location_id": mock_response["location_id"],
                "event_type": "rainfall",
                "description": mock_response["description"],
                "reported_at": mock_response["reported_at"],
            }

            result = await create_citizen_report(report_payload)
            assert result["id"] == mock_response["id"]
            assert result["status"] == "pending"
            mock_post.assert_awaited_once_with(
                "/api/v1/citizen-reports/",
                json_data=report_payload,
            )

    asyncio.run(run())


def test_create_citizen_report_backend_error():
    async def run():
        req = httpx.Request("POST", "http://127.0.0.1:8000/api/v1/citizen-reports/")
        err_resp = httpx.Response(400, request=req, json={"detail": "Location ID does not exist."})

        with patch("api.client.post_json", new_callable=AsyncMock) as mock_post:
            mock_post.side_effect = httpx.HTTPStatusError("400 Bad Request", request=req, response=err_resp)

            with pytest.raises(httpx.HTTPStatusError) as exc_info:
                await create_citizen_report({"location_id": str(uuid4())})

            assert exc_info.value.response.status_code == 400
            assert "Location ID does not exist" in exc_info.value.response.json()["detail"]

    asyncio.run(run())


def test_get_locations_client():
    async def run():
        mock_locs = [
            {"id": str(uuid4()), "name": "Pune", "district": "Pune", "state": "Maharashtra"},
            {"id": str(uuid4()), "name": "Kolhapur", "district": "Kolhapur", "state": "Maharashtra"},
        ]
        with patch("api.client.get_json", new_callable=AsyncMock) as mock_get:
            mock_get.return_value = mock_locs
            locs = await get_locations()
            assert len(locs) == 2
            assert locs[0]["name"] == "Pune"

    asyncio.run(run())


def test_duplicate_submission_lock_simulation():
    # Simulation of the is_submitting_report state flag
    is_submitting_report = False

    def submit_action():
        nonlocal is_submitting_report
        if is_submitting_report:
            return "BLOCKED_DUPLICATE"
        is_submitting_report = True
        return "PROCESSING"

    # First click executes
    res1 = submit_action()
    assert res1 == "PROCESSING"
    assert is_submitting_report is True

    # Immediate second click is blocked
    res2 = submit_action()
    assert res2 == "BLOCKED_DUPLICATE"

    # Reset on completion
    is_submitting_report = False
    res3 = submit_action()
    assert res3 == "PROCESSING"


def test_compatibility_with_existing_verification():
    async def run():
        report_id = str(uuid4())
        mock_verification_result = {
            "report_id": report_id,
            "credibility_score": 0.85,
            "verification_status": "likely_valid",
            "verification_reason": "Matching weather observations found within time window.",
            "model_version": "rule-based-v1",
            "supporting_observations": {"observation_count": 2, "event_count": 1},
        }

        with patch("api.client.post_json", new_callable=AsyncMock) as mock_post:
            mock_post.return_value = mock_verification_result
            res = await verify_citizen_report(report_id)
            assert res["credibility_score"] == 0.85
            assert res["verification_status"] == "likely_valid"
            mock_post.assert_awaited_once_with(f"/api/v1/citizen-reports/{report_id}/verify")

    asyncio.run(run())
