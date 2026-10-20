"""Tests for the WeatherSentinel Model Context Protocol (MCP) Streamable HTTP server."""

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
from app.mcp.server import get_weather_summary, resolve_weather_summary
from app.models.location import Location


class FakeLocationQuery:
    def __init__(self, location):
        self._location = location

    def filter(self, *args, **kwargs):
        return self

    def first(self):
        return self._location


class FakeObservationQuery:
    def __init__(self, observations):
        self._observations = observations

    def filter(self, *args, **kwargs):
        return self

    def count(self):
        return len(self._observations)

    def order_by(self, *args, **kwargs):
        return self

    def offset(self, n):
        return self

    def limit(self, n):
        return self

    def all(self):
        return self._observations


class MockDBSession:
    """Mock database session that records lifecycle state and serves test fixtures."""

    def __init__(self, location=None, observations=None):
        self.location = location
        self.observations = observations or []
        self.closed = False
        self.close_call_count = 0

    def query(self, model):
        if model is Location or getattr(model, "__name__", "") == "Location":
            return FakeLocationQuery(self.location)
        return FakeObservationQuery(self.observations)

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
    mock_obs = SimpleNamespace(
        id=uuid4(),
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
    return mock_loc, mock_obs


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


def test_mcp_initialization_and_protocol_negotiation():
    """Verify MCP protocol initialization, version negotiation (>= 2025-11-25), and server metadata."""

    async def run(session: ClientSession):
        init_result = await session.initialize()
        assert init_result.protocol_version is not None
        # Must be version 2025-11-25 or later as required by Amazon Alexa+ track
        assert init_result.protocol_version >= "2025-11-25"
        assert init_result.server_info.name == "WeatherSentinel MCP Server"
        assert init_result.capabilities.tools is not None

    anyio.run(_run_with_mcp_client, run)


def test_mcp_tool_discovery():
    """Verify tools/list discovers get_weather_summary with proper parameter schema."""

    async def run(session: ClientSession):
        await session.initialize()
        tools_response = await session.list_tools()
        tool_names = [tool.name for tool in tools_response.tools]
        assert "get_weather_summary" in tool_names

        weather_tool = next(t for t in tools_response.tools if t.name == "get_weather_summary")
        assert "weather observation summary" in weather_tool.description.lower()
        properties = weather_tool.input_schema.get("properties", {})
        assert "location_name" in properties
        assert "location_name" in weather_tool.input_schema.get("required", [])

    anyio.run(_run_with_mcp_client, run)


def test_mcp_call_tool_valid_location_with_observations(mock_pune_data):
    """Verify tools/call retrieves genuine structured weather observations for a valid location."""
    mock_loc, mock_obs = mock_pune_data
    session_double = MockDBSession(location=mock_loc, observations=[mock_obs])

    async def run(session: ClientSession):
        await session.initialize()
        with patch("app.mcp.server.SessionLocal", return_value=session_double):
            result = await session.call_tool(
                "get_weather_summary",
                {"location_name": "Pune"},
            )

        assert result.is_error is False
        assert len(result.content) >= 1
        payload = json.loads(result.content[0].text)

        assert payload["status"] == "success"
        assert payload["found"] is True
        assert payload["location"]["name"] == "Pune"
        assert payload["location"]["state"] == "Maharashtra"
        assert payload["observation"]["temperature_c"] == 28.5
        assert payload["observation"]["humidity_pct"] == 65.0
        assert payload["observation"]["condition"] == "Partly Cloudy"
        assert payload["observation"]["source"] == "MOCK_STATION"
        assert "28.5°C" in payload["summary"]
        assert session_double.closed is True

    anyio.run(_run_with_mcp_client, run)


def test_mcp_call_tool_unknown_location():
    """Verify tools/call returns a structured not_found response when location is unknown."""
    session_double = MockDBSession(location=None, observations=[])

    async def run(session: ClientSession):
        await session.initialize()
        with patch("app.mcp.server.SessionLocal", return_value=session_double):
            result = await session.call_tool(
                "get_weather_summary",
                {"location_name": "NonexistentLocation"},
            )

        assert result.is_error is False
        payload = json.loads(result.content[0].text)

        assert payload["status"] == "not_found"
        assert payload["found"] is False
        assert "No registered weather station found" in payload["message"]
        assert session_double.closed is True

    anyio.run(_run_with_mcp_client, run)


def test_mcp_call_tool_valid_location_no_observations(mock_pune_data):
    """Verify tools/call handles a registered location that has no recorded observations."""
    mock_loc, _ = mock_pune_data
    session_double = MockDBSession(location=mock_loc, observations=[])

    async def run(session: ClientSession):
        await session.initialize()
        with patch("app.mcp.server.SessionLocal", return_value=session_double):
            result = await session.call_tool(
                "get_weather_summary",
                {"location_name": "Pune"},
            )

        assert result.is_error is False
        payload = json.loads(result.content[0].text)

        assert payload["status"] == "no_data"
        assert payload["found"] is True
        assert payload["location"]["name"] == "Pune"
        assert payload["observation"] is None
        assert "has no recorded weather observations" in payload["message"]
        assert session_double.closed is True

    anyio.run(_run_with_mcp_client, run)


def test_mcp_call_tool_missing_and_invalid_arguments():
    """Verify tools/call enforces argument validation for missing and blank parameters."""

    async def run(session: ClientSession):
        await session.initialize()

        # Missing argument
        missing_arg_result = await session.call_tool(
            "get_weather_summary",
            {},
        )
        assert missing_arg_result.is_error is True
        assert "location_name" in missing_arg_result.content[0].text

        # Invalid blank argument
        blank_arg_result = await session.call_tool(
            "get_weather_summary",
            {"location_name": "   "},
        )
        assert blank_arg_result.is_error is False
        payload = json.loads(blank_arg_result.content[0].text)
        assert payload["status"] == "error"
        assert payload["found"] is False
        assert "non-empty string" in payload["message"]

    anyio.run(_run_with_mcp_client, run)


def test_mcp_session_lifecycle_and_clean_shutdown():
    """Verify complete session lifecycle from startup to clean shutdown."""

    async def run(session: ClientSession):
        init_result = await session.initialize()
        assert init_result.protocol_version is not None
        tools = await session.list_tools()
        assert len(tools.tools) >= 1

    # Running this completes startup, negotiation, listing, and graceful exit
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


def test_database_session_closed_and_not_leaked(mock_pune_data):
    """Verify that database sessions created by get_weather_summary are always closed cleanly."""
    mock_loc, mock_obs = mock_pune_data
    session_double = MockDBSession(location=mock_loc, observations=[mock_obs])

    with patch("app.mcp.server.SessionLocal", return_value=session_double):
        result = get_weather_summary("Pune")

    assert result["status"] == "success"
    assert session_double.closed is True
    assert session_double.close_call_count == 1
