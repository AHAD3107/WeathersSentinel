"""WeatherSentinel Model Context Protocol (MCP) Integration.

Exposes genuine WeatherSentinel telemetry, event detection, ground-truth citizen
verification, and ML forecasts to MCP-compatible clients including Alexa+.
"""

from app.mcp.server import (
    get_evidence_based_briefing,
    get_mcp_app,
    get_temperature_forecast,
    get_verification_status,
    get_weather_events,
    get_weather_summary,
    mcp_server,
    resolve_evidence_based_briefing,
    resolve_location,
    resolve_temperature_forecast,
    resolve_verification_status,
    resolve_weather_events,
    resolve_weather_summary,
)

__all__ = [
    "get_evidence_based_briefing",
    "get_mcp_app",
    "get_temperature_forecast",
    "get_verification_status",
    "get_weather_events",
    "get_weather_summary",
    "mcp_server",
    "resolve_evidence_based_briefing",
    "resolve_location",
    "resolve_temperature_forecast",
    "resolve_verification_status",
    "resolve_weather_events",
    "resolve_weather_summary",
]
