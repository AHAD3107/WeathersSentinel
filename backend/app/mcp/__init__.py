"""WeatherSentinel Model Context Protocol (MCP) Integration.

Exposes genuine WeatherSentinel telemetry and forecasting intelligence
to MCP-compatible clients including Alexa+, Claude, and custom assistants.
"""

from app.mcp.server import (
    get_mcp_app,
    get_weather_summary,
    mcp_server,
    resolve_weather_summary,
)

__all__ = [
    "get_mcp_app",
    "get_weather_summary",
    "mcp_server",
    "resolve_weather_summary",
]
