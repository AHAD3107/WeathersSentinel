"""Tests for the WeatherSentinel Model Context Protocol (MCP) Streamable HTTP server.

Covers all Phase 1 and Phase 2 tools:
- get_weather_summary
- get_weather_events
- get_verification_status
- get_temperature_forecast
- get_evidence_based_briefing
"""

from datetime import datetime, timezone
from decimal import Decimal
import json
from types import SimpleNamespace
from unittest.mock import patch
from uuid import uuid4

import anyio
from fastapi.testclient import TestClient
import httpx2
from mcp.client.session import ClientSession
from mcp.client.streamable_http import streamable_http_client
import pytest

from app.main import app, lifespan
from app.mcp.server import (
    get_evidence_based_briefing,
    get_temperature_forecast,
    get_verification_status,
    get_weather_events,
    get_weather_summary,
)


class GenericFakeQuery:
    def __init__(self, items):
        self._items = list(items) if items is not None else []

    def filter(self, *args, **kwargs):
        return self

    def join(self, *args, **kwargs):
        return self

    def count(self):
        return len(self._items)

    def order_by(self, *args, **kwargs):
        return self

    def offset(self, n):
        return self

    def limit(self, n):
        return self

    def first(self):
        return self._items[0] if self._items else None

    def all(self):
        return list(self._items)


class MockDBSession:
    """Mock database session that records lifecycle and prevents writes."""

    def __init__(
        self,
        locations=None,
        observations=None,
        events=None,
        forecasts=None,
        reports=None,
        verifications=None,
    ):
        self.locations = locations or []
        self.observations = observations or []
        self.events = events or []
        self.forecasts = forecasts or []
        self.reports = reports or []
        self.verifications = verifications or []
        self.closed = False
        self.close_call_count = 0
        self.add_call_count = 0
        self.commit_call_count = 0

    def query(self, model):
        name = getattr(model, "__name__", str(model))
        if "Location" in name:
            return GenericFakeQuery(self.locations)
        elif "WeatherObservation" in name:
            return GenericFakeQuery(self.observations)
        elif "WeatherEvent" in name:
            return GenericFakeQuery(self.events)
        elif "TemperatureForecast" in name:
            return GenericFakeQuery(self.forecasts)
        elif "CitizenReport" in name:
            return GenericFakeQuery(self.reports)
        elif "VerificationResult" in name:
            return GenericFakeQuery(self.verifications)
        return GenericFakeQuery([])

    def add(self, obj):
        self.add_call_count += 1

    def commit(self):
        self.commit_call_count += 1

    def close(self):
        self.closed = True
        self.close_call_count += 1


@pytest.fixture
def mock_pune_data():
    loc_id = uuid4()
    mock_loc = SimpleNamespace(
        id=loc_id,
        name="Pune",
        district="Pune",
        state="Maharashtra",
        country="India",
        latitude=Decimal("18.5204"),
        longitude=Decimal("73.8567"),
    )
    obs_id = uuid4()
    mock_obs = SimpleNamespace(
        id=obs_id,
        location_id=loc_id,
        source="MOCK_STATION",
        observed_at=datetime(2026, 10, 19, 12, 0, tzinfo=timezone.utc),
        temperature=Decimal("28.50"),
        humidity=Decimal("65.00"),
        pressure=Decimal("1013.25"),
        rainfall=Decimal("0.00"),
        wind_speed=Decimal("12.50"),
        wind_direction=Decimal("180.00"),
        visibility=Decimal("10.00"),
        weather_condition="Partly Cloudy",
        raw_data={},
        created_at=datetime(2026, 10, 19, 12, 0, tzinfo=timezone.utc),
    )
    mock_event = SimpleNamespace(
        id=uuid4(),
        location_id=loc_id,
        event_type="rainfall",
        start_time=datetime(2026, 10, 19, 11, 0, tzinfo=timezone.utc),
        end_time=datetime(2026, 10, 19, 13, 0, tzinfo=timezone.utc),
        severity="moderate",
        confidence_score=Decimal("0.85"),
        source="RULE_ENGINE",
        created_at=datetime(2026, 10, 19, 11, 0, tzinfo=timezone.utc),
    )
    mock_forecast = SimpleNamespace(
        id=uuid4(),
        observation_id=obs_id,
        model_name="random_forest",
        location="Pune, Maharashtra, India",
        forecast_horizon_hours=3,
        predicted_temperature_c=Decimal("29.20"),
        created_at=datetime.now(timezone.utc),
    )
    rep_id = uuid4()
    mock_report = SimpleNamespace(
        id=rep_id,
        user_id=uuid4(),
        location_id=loc_id,
        event_type="rainfall",
        description="Moderate rainfall observed near Shivaji Nagar.",
        reported_at=datetime(2026, 10, 19, 11, 30, tzinfo=timezone.utc),
        image_url="http://example.com/evidence.jpg",
        status="verified",
        created_at=datetime(2026, 10, 19, 11, 30, tzinfo=timezone.utc),
    )
    mock_vr = SimpleNamespace(
        id=uuid4(),
        report_id=rep_id,
        credibility_score=Decimal("0.85"),
        verification_status="likely_valid",
        supporting_observations={"observation_count": 1, "event_count": 1},
        verification_reason="Supporting weather observations found within the time window.",
        model_version="rule-based-v1",
        created_at=datetime(2026, 10, 19, 11, 35, tzinfo=timezone.utc),
    )
    return {
        "location": mock_loc,
        "observation": mock_obs,
        "event": mock_event,
        "forecast": mock_forecast,
        "report": mock_report,
        "verification": mock_vr,
    }


async def _run_with_mcp_client(callback):
    """Helper to run an async test against the mounted FastAPI MCP endpoint."""
    async with lifespan(app):
        transport = httpx2.ASGITransport(app=app)
        async with httpx2.AsyncClient(
            transport=transport,
            base_url="http://127.0.0.1:8000",
        ) as http_client:
            async with streamable_http_client(
                "http://127.0.0.1:8000/mcp",
                http_client=http_client,
            ) as (read_stream, write_stream):
                async with ClientSession(read_stream, write_stream) as session:
                    await callback(session)


# ============================================================================
# Phase 1 & 2 MCP Protocol & Discovery Tests
# ============================================================================

def test_mcp_initialization_and_protocol_negotiation():
    """Verify MCP protocol initialization, version negotiation (>= 2025-11-25), and server metadata."""

    async def run(session: ClientSession):
        init_result = await session.initialize()
        assert init_result.protocol_version is not None
        assert init_result.protocol_version >= "2025-11-25"
        assert init_result.server_info.name == "WeatherSentinel MCP Server"
        assert init_result.capabilities.tools is not None

    anyio.run(_run_with_mcp_client, run)


def test_mcp_tool_discovery_all_five_tools():
    """Verify tools/list discovers all five WeatherSentinel intelligence tools."""

    async def run(session: ClientSession):
        await session.initialize()
        tools_response = await session.list_tools()
        tool_names = [tool.name for tool in tools_response.tools]

        expected_tools = [
            "get_weather_summary",
            "get_weather_events",
            "get_verification_status",
            "get_temperature_forecast",
            "get_evidence_based_briefing",
        ]
        for name in expected_tools:
            assert name in tool_names

        # Validate parameter schemas
        events_tool = next(t for t in tools_response.tools if t.name == "get_weather_events")
        assert "location_name" in events_tool.input_schema.get("required", [])

        briefing_tool = next(t for t in tools_response.tools if t.name == "get_evidence_based_briefing")
        assert "location_name" in briefing_tool.input_schema.get("required", [])

    anyio.run(_run_with_mcp_client, run)


# ============================================================================
# Tool 1: get_weather_summary Tests
# ============================================================================

def test_mcp_call_tool_valid_location_with_observations(mock_pune_data):
    """Verify get_weather_summary retrieves genuine observation values."""
    session_double = MockDBSession(
        locations=[mock_pune_data["location"]],
        observations=[mock_pune_data["observation"]],
    )

    async def run(session: ClientSession):
        await session.initialize()
        with patch("app.mcp.server.SessionLocal", return_value=session_double):
            result = await session.call_tool(
                "get_weather_summary",
                {"location_name": "Pune"},
            )

        assert result.is_error is False
        payload = json.loads(result.content[0].text)
        assert payload["status"] == "success"
        assert payload["found"] is True
        assert payload["location"]["name"] == "Pune"
        assert payload["observation"]["temperature_c"] == 28.5
        assert "28.5°C" in payload["summary"]
        assert session_double.closed is True

    anyio.run(_run_with_mcp_client, run)


def test_mcp_call_tool_ambiguous_location():
    """Verify tools return an ambiguous status listing candidates when a query matches multiple stations."""
    loc1 = SimpleNamespace(
        id=uuid4(),
        name="Pune North Station",
        district="Pune",
        state="Maharashtra",
        country="India",
        latitude=Decimal("18.52"),
        longitude=Decimal("73.85"),
    )
    loc2 = SimpleNamespace(
        id=uuid4(),
        name="Pune South Station",
        district="Pune",
        state="Maharashtra",
        country="India",
        latitude=Decimal("18.50"),
        longitude=Decimal("73.80"),
    )
    session_double = MockDBSession(locations=[loc1, loc2])

    async def run(session: ClientSession):
        await session.initialize()
        with patch("app.mcp.server.SessionLocal", return_value=session_double):
            result = await session.call_tool(
                "get_weather_summary",
                {"location_name": "Pune"},
            )

        assert result.is_error is False
        payload = json.loads(result.content[0].text)
        assert payload["status"] == "ambiguous"
        assert payload["found"] is False
        assert len(payload["candidates"]) >= 2
        assert "Multiple locations matched" in payload["message"]

    anyio.run(_run_with_mcp_client, run)


# ============================================================================
# Tool 2: get_weather_events Tests
# ============================================================================

def test_mcp_get_weather_events_success(mock_pune_data):
    """Verify get_weather_events returns genuine recorded events."""
    session_double = MockDBSession(
        locations=[mock_pune_data["location"]],
        events=[mock_pune_data["event"]],
    )

    async def run(session: ClientSession):
        await session.initialize()
        with patch("app.mcp.server.SessionLocal", return_value=session_double):
            result = await session.call_tool(
                "get_weather_events",
                {"location_name": "Pune", "limit": 5},
            )

        assert result.is_error is False
        payload = json.loads(result.content[0].text)
        assert payload["status"] == "success"
        assert payload["found"] is True
        assert payload["total"] == 1
        assert payload["events"][0]["event_type"] == "rainfall"
        assert payload["events"][0]["severity"] == "moderate"
        assert payload["events"][0]["confidence_score"] == 0.85

    anyio.run(_run_with_mcp_client, run)


def test_mcp_get_weather_events_no_events(mock_pune_data):
    """Verify get_weather_events handles locations without recorded events."""
    session_double = MockDBSession(
        locations=[mock_pune_data["location"]],
        events=[],
    )

    async def run(session: ClientSession):
        await session.initialize()
        with patch("app.mcp.server.SessionLocal", return_value=session_double):
            result = await session.call_tool(
                "get_weather_events",
                {"location_name": "Pune"},
            )

        assert result.is_error is False
        payload = json.loads(result.content[0].text)
        assert payload["status"] == "no_events"
        assert payload["total"] == 0
        assert "No weather events recorded" in payload["message"]

    anyio.run(_run_with_mcp_client, run)


# ============================================================================
# Tool 3: get_verification_status Tests
# ============================================================================

def test_mcp_get_verification_status_by_location(mock_pune_data):
    """Verify get_verification_status retrieves reports and verifications for a location without PII."""
    session_double = MockDBSession(
        locations=[mock_pune_data["location"]],
        reports=[mock_pune_data["report"]],
        verifications=[mock_pune_data["verification"]],
    )

    async def run(session: ClientSession):
        await session.initialize()
        with patch("app.mcp.server.SessionLocal", return_value=session_double):
            result = await session.call_tool(
                "get_verification_status",
                {"location_name": "Pune"},
            )

        assert result.is_error is False
        payload = json.loads(result.content[0].text)
        assert payload["status"] == "success"
        assert payload["total"] == 1
        rep = payload["reports"][0]
        assert rep["report_lifecycle_status"] == "verified"
        assert rep["verification"]["verification_status"] == "likely_valid"
        assert rep["verification"]["credibility_score"] == 0.85
        # Ensure citizen PII is omitted
        assert "user_id" not in rep
        assert "email" not in rep

    anyio.run(_run_with_mcp_client, run)


def test_mcp_get_verification_status_by_report_id(mock_pune_data):
    """Verify get_verification_status retrieves a specific report by UUID."""
    session_double = MockDBSession(
        locations=[mock_pune_data["location"]],
        reports=[mock_pune_data["report"]],
        verifications=[mock_pune_data["verification"]],
    )

    async def run(session: ClientSession):
        await session.initialize()
        with patch("app.mcp.server.SessionLocal", return_value=session_double):
            result = await session.call_tool(
                "get_verification_status",
                {"report_id": str(mock_pune_data["report"].id)},
            )

        assert result.is_error is False
        payload = json.loads(result.content[0].text)
        assert payload["status"] == "success"
        assert payload["report_id"] == str(mock_pune_data["report"].id)
        assert payload["verification"]["verification_status"] == "likely_valid"

    anyio.run(_run_with_mcp_client, run)


def test_mcp_get_verification_status_different_outcomes(mock_pune_data):
    """Verify get_verification_status correctly reflects different verification outcomes (uncertain, likely_misleading)."""
    rep = mock_pune_data["report"]
    vr_uncertain = SimpleNamespace(
        id=uuid4(),
        report_id=rep.id,
        credibility_score=Decimal("0.50"),
        verification_status="uncertain",
        supporting_observations={},
        verification_reason="Partial observation match.",
        model_version="rule-based-v1",
        created_at=datetime(2026, 10, 19, 12, 0, tzinfo=timezone.utc),
    )
    session_double = MockDBSession(
        locations=[mock_pune_data["location"]],
        reports=[rep],
        verifications=[vr_uncertain],
    )

    async def run(session: ClientSession):
        await session.initialize()
        with patch("app.mcp.server.SessionLocal", return_value=session_double):
            result = await session.call_tool(
                "get_verification_status",
                {"report_id": str(rep.id)},
            )

        assert result.is_error is False
        payload = json.loads(result.content[0].text)
        assert payload["verification"]["verification_status"] == "uncertain"
        assert payload["verification"]["credibility_score"] == 0.50

    anyio.run(_run_with_mcp_client, run)


# ============================================================================
# Tool 4: get_temperature_forecast Tests
# ============================================================================

def test_mcp_get_temperature_forecast_success(mock_pune_data):
    """Verify get_temperature_forecast returns persisted forecasts with freshness metadata."""
    session_double = MockDBSession(
        locations=[mock_pune_data["location"]],
        forecasts=[mock_pune_data["forecast"]],
    )

    async def run(session: ClientSession):
        await session.initialize()
        with patch("app.mcp.server.SessionLocal", return_value=session_double):
            result = await session.call_tool(
                "get_temperature_forecast",
                {"location_name": "Pune"},
            )

        assert result.is_error is False
        payload = json.loads(result.content[0].text)
        assert payload["status"] == "success"
        fc = payload["forecast"]
        assert fc["predicted_temperature_c"] == 29.20
        assert fc["forecast_horizon_hours"] == 3
        assert fc["model_name"] == "random_forest"
        assert "valid_until" in fc
        assert isinstance(fc["is_stale"], bool)

    anyio.run(_run_with_mcp_client, run)


def test_mcp_get_temperature_forecast_no_forecast(mock_pune_data):
    """Verify get_temperature_forecast returns structured no_forecast when none exists."""
    session_double = MockDBSession(
        locations=[mock_pune_data["location"]],
        forecasts=[],
    )

    async def run(session: ClientSession):
        await session.initialize()
        with patch("app.mcp.server.SessionLocal", return_value=session_double):
            result = await session.call_tool(
                "get_temperature_forecast",
                {"location_name": "Pune"},
            )

        assert result.is_error is False
        payload = json.loads(result.content[0].text)
        assert payload["status"] == "no_forecast"
        assert payload["forecast"] is None
        assert "No saved temperature forecasts found" in payload["message"]

    anyio.run(_run_with_mcp_client, run)


# ============================================================================
# Tool 5: get_evidence_based_briefing Tests
# ============================================================================

def test_mcp_get_evidence_based_briefing_full(mock_pune_data):
    """Verify get_evidence_based_briefing coordinates all evidence streams and builds narrative."""
    session_double = MockDBSession(
        locations=[mock_pune_data["location"]],
        observations=[mock_pune_data["observation"]],
        events=[mock_pune_data["event"]],
        forecasts=[mock_pune_data["forecast"]],
        reports=[mock_pune_data["report"]],
        verifications=[mock_pune_data["verification"]],
    )

    async def run(session: ClientSession):
        await session.initialize()
        with patch("app.mcp.server.SessionLocal", return_value=session_double):
            result = await session.call_tool(
                "get_evidence_based_briefing",
                {"location_name": "Pune"},
            )

        assert result.is_error is False
        payload = json.loads(result.content[0].text)
        assert payload["status"] == "success"
        assert payload["observation"]["temperature_c"] == 28.5
        assert payload["weather_events"]["total"] == 1
        assert payload["temperature_forecast"]["predicted_temperature_c"] == 29.20
        assert payload["citizen_verifications"]["total"] == 1
        assert len(payload["voice_narrative"]) > 20
        assert "Pune" in payload["voice_narrative"]
        assert "28.5" in payload["voice_narrative"]

    anyio.run(_run_with_mcp_client, run)


def test_mcp_get_evidence_based_briefing_partial_data(mock_pune_data):
    """Verify get_evidence_based_briefing safely handles missing components and lists data gaps."""
    # Only location and observation, no events, no forecast, no reports
    session_double = MockDBSession(
        locations=[mock_pune_data["location"]],
        observations=[mock_pune_data["observation"]],
        events=[],
        forecasts=[],
        reports=[],
        verifications=[],
    )

    async def run(session: ClientSession):
        await session.initialize()
        with patch("app.mcp.server.SessionLocal", return_value=session_double):
            result = await session.call_tool(
                "get_evidence_based_briefing",
                {"location_name": "Pune"},
            )

        assert result.is_error is False
        payload = json.loads(result.content[0].text)
        assert payload["status"] == "success"
        assert payload["observation"]["temperature_c"] == 28.5
        assert payload["weather_events"]["total"] == 0
        assert payload["temperature_forecast"] is None
        assert payload["citizen_verifications"]["total"] == 0
        # Uncertainty / data gaps explicitly documented
        assert len(payload["data_gaps"]) >= 3
        assert "voice_narrative" in payload

    anyio.run(_run_with_mcp_client, run)


# ============================================================================
# Security, Validation & Read-Only Tests
# ============================================================================

def test_mcp_missing_and_invalid_arguments():
    """Verify argument validation across new tools."""

    async def run(session: ClientSession):
        await session.initialize()

        # Missing required location_name
        res1 = await session.call_tool("get_weather_events", {})
        assert res1.is_error is True

        res2 = await session.call_tool("get_temperature_forecast", {})
        assert res2.is_error is True

        # Invalid report_id in get_verification_status
        res3 = await session.call_tool(
            "get_verification_status",
            {"report_id": "not-a-valid-uuid"},
        )
        assert res3.is_error is False
        payload = json.loads(res3.content[0].text)
        assert payload["status"] == "error"
        assert "Invalid report_id format" in payload["message"]

    anyio.run(_run_with_mcp_client, run)


def test_mcp_read_only_guarantee(mock_pune_data):
    """Verify tools are strictly read-only and never invoke db.add or db.commit."""
    session_double = MockDBSession(
        locations=[mock_pune_data["location"]],
        observations=[mock_pune_data["observation"]],
        events=[mock_pune_data["event"]],
        forecasts=[mock_pune_data["forecast"]],
        reports=[mock_pune_data["report"]],
        verifications=[mock_pune_data["verification"]],
    )

    with patch("app.mcp.server.SessionLocal", return_value=session_double):
        get_weather_summary("Pune")
        get_weather_events("Pune")
        get_temperature_forecast("Pune")
        get_verification_status(location_name="Pune")
        get_evidence_based_briefing("Pune")

    assert session_double.add_call_count == 0
    assert session_double.commit_call_count == 0


def test_mcp_session_lifecycle_and_clean_shutdown():
    """Verify complete session lifecycle from startup to clean shutdown."""

    async def run(session: ClientSession):
        init_result = await session.initialize()
        assert init_result.protocol_version is not None
        tools = await session.list_tools()
        assert len(tools.tools) == 5

    anyio.run(_run_with_mcp_client, run)


def test_existing_fastapi_health_and_weather_endpoints_accessible():
    """Verify existing FastAPI endpoints remain completely functional after MCP mounting."""
    with TestClient(app, base_url="http://127.0.0.1:8000") as client:
        # Root endpoint
        root_res = client.get("/")
        assert root_res.status_code == 200
        assert root_res.json() == {"message": "WeatherSentinel API is running"}

        # Health endpoint
        health_res = client.get("/health/")
        assert health_res.status_code == 200
        assert health_res.json()["status"] == "ok"

        # Locations endpoint
        locations_res = client.get("/api/v1/locations/")
        assert locations_res.status_code == 200
        assert isinstance(locations_res.json(), list)

        # Weather observations endpoint
        weather_res = client.get("/api/v1/weather-observations/")
        assert weather_res.status_code == 200
        assert "items" in weather_res.json()
