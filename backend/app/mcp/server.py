from typing import Any
from starlette.applications import Starlette
from sqlalchemy.orm import Session

from mcp.server import MCPServer
from app.database import SessionLocal
from app.models.location import Location
from app.services.weather_service import get_weather_observations

mcp_server = MCPServer("WeatherSentinel MCP Server")


class MCPASGIProxy:
    """ASGI proxy wrapper allowing the MCP StreamableHTTP session manager
    to be safely refreshed across multiple application lifespans (e.g. test clients)
    while presenting a stable ASGI interface to FastAPI mount.
    """

    def __init__(self, server: MCPServer) -> None:
        self.server = server
        self._app: Starlette = server.streamable_http_app()

    def refresh(self) -> None:
        self._app = self.server.streamable_http_app()

    async def __call__(self, scope: Any, receive: Any, send: Any) -> None:
        await self._app(scope, receive, send)


mcp_proxy = MCPASGIProxy(mcp_server)


def resolve_weather_summary(db: Session, location_name: str) -> dict[str, Any]:
    """Internal helper to resolve location and observations using a provided SQLAlchemy session."""
    if not isinstance(location_name, str) or not location_name.strip():
        return {
            "status": "error",
            "query": location_name if isinstance(location_name, str) else None,
            "found": False,
            "message": "location_name must be a non-empty string.",
        }

    clean_name = location_name.strip()

    # Query location: exact match -> prefix match -> substring match -> district match
    location = (
        db.query(Location).filter(Location.name.ilike(clean_name)).first()
        or db.query(Location).filter(Location.name.ilike(f"{clean_name}%")).first()
        or db.query(Location).filter(Location.name.ilike(f"%{clean_name}%")).first()
        or db.query(Location).filter(Location.district.ilike(clean_name)).first()
    )

    if location is None:
        return {
            "status": "not_found",
            "query": location_name,
            "found": False,
            "message": f"No registered weather station found matching '{clean_name}'.",
        }

    location_data = {
        "id": str(location.id),
        "name": location.name,
        "district": location.district,
        "state": location.state,
        "country": location.country,
        "latitude": float(location.latitude) if location.latitude is not None else None,
        "longitude": float(location.longitude) if location.longitude is not None else None,
    }

    # Fetch latest genuine observation via existing weather service
    observations, total = get_weather_observations(
        db=db,
        location_id=location.id,
        page=1,
        page_size=1,
    )

    if not observations or total == 0:
        return {
            "status": "no_data",
            "query": location_name,
            "found": True,
            "location": location_data,
            "message": f"Location '{location.name}' is registered, but has no recorded weather observations.",
            "observation": None,
        }

    obs = observations[0]
    temp_val = float(obs.temperature) if obs.temperature is not None else None
    hum_val = float(obs.humidity) if obs.humidity is not None else None
    press_val = float(obs.pressure) if obs.pressure is not None else None
    rain_val = float(obs.rainfall) if obs.rainfall is not None else None
    wind_spd = float(obs.wind_speed) if obs.wind_speed is not None else None
    wind_dir = float(obs.wind_direction) if obs.wind_direction is not None else None
    vis_val = float(obs.visibility) if obs.visibility is not None else None

    obs_data = {
        "id": str(obs.id),
        "observed_at": obs.observed_at.isoformat() if obs.observed_at else None,
        "source": obs.source,
        "temperature_c": temp_val,
        "humidity_pct": hum_val,
        "pressure_hpa": press_val,
        "rainfall_mm": rain_val,
        "wind_speed_kmh": wind_spd,
        "wind_direction_deg": wind_dir,
        "visibility_km": vis_val,
        "condition": obs.weather_condition,
    }

    temp_text = f"{temp_val}°C" if temp_val is not None else "unavailable"
    cond_text = obs.weather_condition or "recorded weather"
    hum_text = f"{hum_val}%" if hum_val is not None else "N/A"
    wind_text = f"{wind_spd} km/h" if wind_spd is not None else "N/A"
    state_text = f", {location.state}" if location.state else ""

    summary_text = (
        f"Latest observation for {location.name}{state_text}: {cond_text} at {temp_text}, "
        f"humidity {hum_text}, wind {wind_text}."
    )

    return {
        "status": "success",
        "query": location_name,
        "found": True,
        "location": location_data,
        "observation": obs_data,
        "summary": summary_text,
    }


@mcp_server.tool()
def get_weather_summary(location_name: str) -> dict[str, Any]:
    """Retrieve the latest genuine weather observation summary for a registered location in WeatherSentinel.

    Args:
        location_name: Name of the city, station, or district to retrieve weather for (e.g. 'Pune').

    Returns:
        Structured weather data including temperature, humidity, wind, condition, timestamp, and source.
    """
    db = SessionLocal()
    try:
        return resolve_weather_summary(db, location_name)
    finally:
        db.close()


def get_mcp_app() -> MCPASGIProxy:
    """Return the Starlette ASGI application proxy for the WeatherSentinel MCP server.

    Mounts Streamable HTTP at /mcp with local DNS-rebinding protection enabled.
    """
    return mcp_proxy
