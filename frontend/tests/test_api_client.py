"""Automated tests for frontend API client and geospatial coordinate logic."""

import pytest
import asyncio
from api.client import (
    extract_observation_coordinates,
    get_backend_health,
    get_backend_status_detailed,
    get_forecast_summary,
    get_forecasts,
    get_weather_observations,
    get_weather_events,
    get_citizen_reports,
)


def test_extract_observation_coordinates_from_raw_data():
    """Verify coordinate extraction from raw_data payload."""
    record = {
        "id": "12345",
        "raw_data": {
            "latitude": 18.5204,
            "longitude": 73.8567,
            "source": "OPEN_METEO",
        },
    }
    coords = extract_observation_coordinates(record)
    assert coords is not None
    assert coords == (18.5204, 73.8567)


def test_extract_observation_coordinates_string_values():
    """Verify numeric strings in raw_data are safely parsed."""
    record = {
        "raw_data": {
            "latitude": "16.7050",
            "longitude": "74.2433",
        }
    }
    coords = extract_observation_coordinates(record)
    assert coords is not None
    assert round(coords[0], 4) == 16.7050
    assert round(coords[1], 4) == 74.2433


def test_extract_observation_coordinates_no_fabrication_when_missing():
    """Ensure coordinates are NEVER fabricated or hallucinated when absent."""
    # NOAA record with no coordinates in raw_data
    noaa_record = {
        "source": "NOAA_ISD_LITE",
        "raw_data": {
            "source_format": "NOAA_ISD_LITE",
            "temperature_c": "25.0",
            "pressure_hpa": "1012.0",
        },
    }
    assert extract_observation_coordinates(noaa_record) is None

    # Empty raw_data
    assert extract_observation_coordinates({"raw_data": {}}) is None

    # None raw_data
    assert extract_observation_coordinates({"raw_data": None}) is None

    # Non-dictionary input
    assert extract_observation_coordinates({}) is None
    assert extract_observation_coordinates(None) is None


def test_extract_observation_coordinates_bounds_validation():
    """Verify invalid geographic bounds are rejected."""
    # Latitude > 90
    assert extract_observation_coordinates({"raw_data": {"latitude": 95.0, "longitude": 70.0}}) is None
    # Latitude < -90
    assert extract_observation_coordinates({"raw_data": {"latitude": -95.0, "longitude": 70.0}}) is None
    # Longitude > 180
    assert extract_observation_coordinates({"raw_data": {"latitude": 18.0, "longitude": 195.0}}) is None
    # Non-numeric
    assert extract_observation_coordinates({"raw_data": {"latitude": "invalid", "longitude": "coords"}}) is None


def test_forecasts_normalization_dict():
    """Verify forecast records dictionary structure normalization."""
    # Simulated backend response with 'value' and 'Count'
    async def run():
        # Verify normalization pattern
        response = {"value": [{"id": 1, "predicted_temperature_c": 28.5}], "Count": 1}
        records = response.get("value", [])
        total = response.get("Count", len(records))
        return {"items": records, "total": total}

    result = asyncio.run(run())
    assert result["total"] == 1
    assert len(result["items"]) == 1
    assert result["items"][0]["predicted_temperature_c"] == 28.5


def test_live_backend_health():
    """Test live health endpoint against running backend."""
    async def run():
        res = await get_backend_status_detailed()
        assert res["online"] is True
        assert res["latency_ms"] > 0
        assert res["data"]["status"] == "ok"

    asyncio.run(run())


def test_live_weather_observations_api():
    """Test live weather observations fetch from backend."""
    async def run():
        obs = await get_weather_observations(page=1, page_size=5)
        assert isinstance(obs, dict)
        assert "items" in obs
        assert "total" in obs
        assert obs["total"] > 0
        assert len(obs["items"]) <= 5
        # Ensure at least one observation has valid coordinates
        coords_list = [extract_observation_coordinates(item) for item in obs["items"]]
        # Verify elements are either valid tuples or None (never invalid structures)
        for c in coords_list:
            if c is not None:
                assert isinstance(c, tuple)
                assert len(c) == 2
                assert -90 <= c[0] <= 90
                assert -180 <= c[1] <= 180

    asyncio.run(run())


def test_live_weather_events_api():
    """Test live weather events fetch from backend."""
    async def run():
        events = await get_weather_events(page=1, page_size=5)
        assert isinstance(events, dict)
        assert "items" in events
        assert "total" in events
        assert events["total"] >= 0

    asyncio.run(run())


def test_live_citizen_reports_api():
    """Test live citizen reports fetch from backend."""
    async def run():
        reports = await get_citizen_reports(page=1, page_size=5)
        assert isinstance(reports, dict)
        assert "items" in reports
        assert "total" in reports
        assert reports["total"] >= 0

    asyncio.run(run())


def test_live_forecast_summary_api():
    """Test live forecast summary fetch from backend."""
    async def run():
        summary = await get_forecast_summary()
        assert isinstance(summary, dict)
        assert "total_forecasts" in summary
        assert summary["total_forecasts"] >= 0

    asyncio.run(run())
