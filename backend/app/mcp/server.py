from datetime import datetime, timedelta, timezone
from typing import Any
from uuid import UUID

from sqlalchemy.orm import Session
from starlette.applications import Starlette

from app.database import SessionLocal
from app.models.citizen_report import CitizenReport
from app.models.location import Location
from app.models.temperature_forecast import TemperatureForecast
from app.models.verification_result import VerificationResult
from app.models.weather_event import WeatherEvent
from app.models.weather_observation import WeatherObservation
from app.services.weather_event_service import get_weather_events as fetch_weather_events
from app.services.weather_service import get_weather_observations
from mcp.server import MCPServer

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


# ============================================================================
# Shared Helper Functions (Reusable across all MCP tools)
# ============================================================================

def resolve_location(db: Session, location_name: str) -> dict[str, Any]:
    """Resolve a location name into a registered Location record safely.

    Prevents silent incorrect matches when a query is ambiguous across stations.

    Returns:
        A dict with:
            - success (bool): True if an unambiguous location was resolved.
            - status (str): "ok", "error", "ambiguous", or "not_found".
            - location (Location | None): Resolved model instance.
            - location_data (dict | None): JSON-serializable location fields.
            - message (str): Informative message if not successful.
            - candidates (list[str] | None): Disambiguation list if ambiguous.
    """
    if not isinstance(location_name, str) or not location_name.strip():
        return {
            "success": False,
            "status": "error",
            "location": None,
            "location_data": None,
            "message": "location_name must be a non-empty string.",
        }

    clean_name = location_name.strip()

    # 1. Exact match (case-insensitive) on name
    exact_matches = db.query(Location).filter(Location.name.ilike(clean_name)).all()
    if exact_matches:
        distinct_names = {l.name for l in exact_matches}
        if len(distinct_names) == 1:
            loc = exact_matches[0]
            return {
                "success": True,
                "status": "ok",
                "location": loc,
                "location_data": {
                    "id": str(loc.id),
                    "name": loc.name,
                    "district": loc.district,
                    "state": loc.state,
                    "country": loc.country,
                    "latitude": float(loc.latitude) if loc.latitude is not None else None,
                    "longitude": float(loc.longitude) if loc.longitude is not None else None,
                },
            }

    # 2. Prefix match
    prefix_matches = db.query(Location).filter(Location.name.ilike(f"{clean_name}%")).all()
    unique_prefix = {l.name: l for l in prefix_matches}
    if len(unique_prefix) == 1:
        loc = next(iter(unique_prefix.values()))
        return {
            "success": True,
            "status": "ok",
            "location": loc,
            "location_data": {
                "id": str(loc.id),
                "name": loc.name,
                "district": loc.district,
                "state": loc.state,
                "country": loc.country,
                "latitude": float(loc.latitude) if loc.latitude is not None else None,
                "longitude": float(loc.longitude) if loc.longitude is not None else None,
            },
        }
    elif len(unique_prefix) > 1:
        candidates = [f"{l.name} ({l.district or l.state})" for l in unique_prefix.values()]
        return {
            "success": False,
            "status": "ambiguous",
            "location": None,
            "location_data": None,
            "candidates": candidates,
            "message": f"Multiple locations matched '{clean_name}': {', '.join(candidates)}. Please specify the exact station or location name.",
        }

    # 3. Substring match
    substr_matches = db.query(Location).filter(Location.name.ilike(f"%{clean_name}%")).all()
    unique_substr = {l.name: l for l in substr_matches}
    if len(unique_substr) == 1:
        loc = next(iter(unique_substr.values()))
        return {
            "success": True,
            "status": "ok",
            "location": loc,
            "location_data": {
                "id": str(loc.id),
                "name": loc.name,
                "district": loc.district,
                "state": loc.state,
                "country": loc.country,
                "latitude": float(loc.latitude) if loc.latitude is not None else None,
                "longitude": float(loc.longitude) if loc.longitude is not None else None,
            },
        }
    elif len(unique_substr) > 1:
        candidates = [f"{l.name} ({l.district or l.state})" for l in unique_substr.values()]
        return {
            "success": False,
            "status": "ambiguous",
            "location": None,
            "location_data": None,
            "candidates": candidates,
            "message": f"Multiple locations matched '{clean_name}': {', '.join(candidates)}. Please specify the exact station or location name.",
        }

    # 4. District match
    district_matches = db.query(Location).filter(Location.district.ilike(clean_name)).all()
    unique_district = {l.name: l for l in district_matches}
    if len(unique_district) == 1:
        loc = next(iter(unique_district.values()))
        return {
            "success": True,
            "status": "ok",
            "location": loc,
            "location_data": {
                "id": str(loc.id),
                "name": loc.name,
                "district": loc.district,
                "state": loc.state,
                "country": loc.country,
                "latitude": float(loc.latitude) if loc.latitude is not None else None,
                "longitude": float(loc.longitude) if loc.longitude is not None else None,
            },
        }
    elif len(unique_district) > 1:
        candidates = [f"{l.name} ({l.district or l.state})" for l in unique_district.values()]
        return {
            "success": False,
            "status": "ambiguous",
            "location": None,
            "location_data": None,
            "candidates": candidates,
            "message": f"Multiple locations found in district '{clean_name}': {', '.join(candidates)}. Please specify the station name.",
        }

    return {
        "success": False,
        "status": "not_found",
        "location": None,
        "location_data": None,
        "message": f"No registered weather station found matching '{clean_name}'.",
    }


def _get_latest_observation(db: Session, location_id: UUID) -> dict[str, Any] | None:
    """Retrieve the latest genuine weather observation for a location."""
    observations, total = get_weather_observations(
        db=db,
        location_id=location_id,
        page=1,
        page_size=1,
    )
    if not observations or total == 0:
        return None

    obs = observations[0]
    return {
        "id": str(obs.id),
        "observed_at": obs.observed_at.isoformat() if obs.observed_at else None,
        "source": obs.source,
        "temperature_c": float(obs.temperature) if obs.temperature is not None else None,
        "humidity_pct": float(obs.humidity) if obs.humidity is not None else None,
        "pressure_hpa": float(obs.pressure) if obs.pressure is not None else None,
        "rainfall_mm": float(obs.rainfall) if obs.rainfall is not None else None,
        "wind_speed_kmh": float(obs.wind_speed) if obs.wind_speed is not None else None,
        "wind_direction_deg": float(obs.wind_direction) if obs.wind_direction is not None else None,
        "visibility_km": float(obs.visibility) if obs.visibility is not None else None,
        "condition": obs.weather_condition,
    }


def _get_events(db: Session, location_id: UUID, limit: int = 5) -> tuple[list[dict[str, Any]], int]:
    """Retrieve genuine recorded weather events for a location."""
    events, total = fetch_weather_events(
        db=db,
        location_id=location_id,
        page=1,
        page_size=limit,
    )
    formatted = [
        {
            "id": str(e.id),
            "event_type": e.event_type,
            "severity": e.severity,
            "start_time": e.start_time.isoformat() if e.start_time else None,
            "end_time": e.end_time.isoformat() if e.end_time else None,
            "confidence_score": float(e.confidence_score) if e.confidence_score is not None else None,
            "source": e.source,
            "created_at": e.created_at.isoformat() if e.created_at else None,
        }
        for e in events
    ]
    return formatted, total


def _get_forecast(db: Session, location_name: str, location_id: UUID) -> dict[str, Any] | None:
    """Retrieve the newest persisted temperature forecast for a location."""
    forecast = (
        db.query(TemperatureForecast)
        .filter(TemperatureForecast.location.ilike(f"%{location_name}%"))
        .order_by(TemperatureForecast.created_at.desc())
        .first()
    )

    if forecast is None:
        forecast = (
            db.query(TemperatureForecast)
            .join(WeatherObservation, TemperatureForecast.observation_id == WeatherObservation.id)
            .filter(WeatherObservation.location_id == location_id)
            .order_by(TemperatureForecast.created_at.desc())
            .first()
        )

    if forecast is None:
        return None

    horizon_hours = forecast.forecast_horizon_hours
    valid_until = forecast.created_at + timedelta(hours=horizon_hours)
    now = datetime.now(timezone.utc)
    is_stale = now > valid_until

    return {
        "id": str(forecast.id),
        "model_name": forecast.model_name,
        "location_label": forecast.location,
        "forecast_horizon_hours": horizon_hours,
        "predicted_temperature_c": float(forecast.predicted_temperature_c),
        "unit": "Celsius",
        "generated_at": forecast.created_at.isoformat(),
        "valid_until": valid_until.isoformat(),
        "is_stale": is_stale,
        "observation_id": str(forecast.observation_id),
    }


def _get_verifications_for_location(
    db: Session,
    location_id: UUID,
    limit: int = 5,
) -> tuple[list[dict[str, Any]], int]:
    """Retrieve citizen report verification results for a location without citizen PII."""
    reports = (
        db.query(CitizenReport)
        .filter(CitizenReport.location_id == location_id)
        .order_by(CitizenReport.reported_at.desc())
        .limit(limit)
        .all()
    )
    total = (
        db.query(CitizenReport)
        .filter(CitizenReport.location_id == location_id)
        .count()
    )

    formatted = []
    for r in reports:
        vr = (
            db.query(VerificationResult)
            .filter(VerificationResult.report_id == r.id)
            .first()
        )
        report_dict = {
            "report_id": str(r.id),
            "event_type": r.event_type,
            "description": r.description,
            "reported_at": r.reported_at.isoformat() if r.reported_at else None,
            "report_lifecycle_status": r.status,
            "has_image_evidence": bool(r.image_url),
            "verification": {
                "verification_status": vr.verification_status if vr else "pending",
                "credibility_score": float(vr.credibility_score) if vr else None,
                "verification_reason": vr.verification_reason if vr else "Verification pending.",
                "supporting_observations": vr.supporting_observations if vr else None,
                "model_version": vr.model_version if vr else None,
                "verified_at": vr.created_at.isoformat() if vr else None,
            },
        }
        formatted.append(report_dict)

    return formatted, total


# ============================================================================
# Core Internal Resolvers (Testable with provided Session)
# ============================================================================

def resolve_weather_summary(db: Session, location_name: str) -> dict[str, Any]:
    """Internal helper to resolve location and observations using a provided SQLAlchemy session."""
    res = resolve_location(db, location_name)
    if not res["success"]:
        return {
            "status": res["status"],
            "query": location_name,
            "found": False,
            "message": res["message"],
            **({"candidates": res["candidates"]} if "candidates" in res else {}),
        }

    loc = res["location"]
    location_data = res["location_data"]

    obs_data = _get_latest_observation(db, loc.id)
    if obs_data is None:
        return {
            "status": "no_data",
            "query": location_name,
            "found": True,
            "location": location_data,
            "message": f"Location '{loc.name}' is registered, but has no recorded weather observations.",
            "observation": None,
        }

    temp_text = f"{obs_data['temperature_c']}°C" if obs_data["temperature_c"] is not None else "unavailable"
    cond_text = obs_data["condition"] or "recorded weather"
    hum_text = f"{obs_data['humidity_pct']}%" if obs_data["humidity_pct"] is not None else "N/A"
    wind_text = f"{obs_data['wind_speed_kmh']} km/h" if obs_data["wind_speed_kmh"] is not None else "N/A"
    state_text = f", {loc.state}" if loc.state else ""

    summary_text = (
        f"Latest observation for {loc.name}{state_text}: {cond_text} at {temp_text}, "
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


def resolve_weather_events(
    db: Session,
    location_name: str,
    limit: int = 5,
) -> dict[str, Any]:
    """Internal helper to retrieve genuine weather events for a location."""
    res = resolve_location(db, location_name)
    if not res["success"]:
        return {
            "status": res["status"],
            "query": location_name,
            "found": False,
            "message": res["message"],
            **({"candidates": res["candidates"]} if "candidates" in res else {}),
        }

    loc = res["location"]
    location_data = res["location_data"]

    effective_limit = max(1, min(limit, 50))
    events, total = _get_events(db, loc.id, limit=effective_limit)

    if not events or total == 0:
        return {
            "status": "no_events",
            "query": location_name,
            "found": True,
            "location": location_data,
            "events": [],
            "total": 0,
            "message": f"No weather events recorded for {loc.name}.",
        }

    event_summaries = [f"{e['severity']} {e['event_type']}" for e in events[:3]]
    summary_text = f"{total} event(s) recorded for {loc.name}: {', '.join(event_summaries)}."

    return {
        "status": "success",
        "query": location_name,
        "found": True,
        "location": location_data,
        "events": events,
        "total": total,
        "summary": summary_text,
    }


def resolve_verification_status(
    db: Session,
    location_name: str | None = None,
    report_id: str | None = None,
) -> dict[str, Any]:
    """Internal helper to retrieve verification statuses without side effects."""
    if not location_name and not report_id:
        return {
            "status": "error",
            "found": False,
            "message": "Either location_name or report_id must be provided.",
        }

    # Query specific report by UUID
    if report_id:
        clean_report_id = report_id.strip() if isinstance(report_id, str) else ""
        try:
            target_uuid = UUID(clean_report_id)
        except (ValueError, TypeError, AttributeError):
            return {
                "status": "error",
                "found": False,
                "message": f"Invalid report_id format '{report_id}'; must be a valid UUID.",
            }

        report = db.query(CitizenReport).filter(CitizenReport.id == target_uuid).first()
        if report is None:
            return {
                "status": "not_found",
                "found": False,
                "report_id": clean_report_id,
                "message": f"Citizen report '{clean_report_id}' was not found.",
            }

        loc = db.query(Location).filter(Location.id == report.location_id).first()
        vr = db.query(VerificationResult).filter(VerificationResult.report_id == report.id).first()

        verification_status = vr.verification_status if vr else "pending"
        credibility_score = float(vr.credibility_score) if vr else None

        return {
            "status": "success",
            "found": True,
            "report_id": str(report.id),
            "event_type": report.event_type,
            "description": report.description,
            "reported_at": report.reported_at.isoformat() if report.reported_at else None,
            "report_lifecycle_status": report.status,
            "has_image_evidence": bool(report.image_url),
            "location": {
                "id": str(loc.id) if loc else str(report.location_id),
                "name": loc.name if loc else "Unknown",
                "state": loc.state if loc else None,
            },
            "verification": {
                "verification_status": verification_status,
                "credibility_score": credibility_score,
                "verification_reason": vr.verification_reason if vr else "Verification has not been performed for this report yet.",
                "supporting_observations": vr.supporting_observations if vr else None,
                "model_version": vr.model_version if vr else None,
                "verified_at": vr.created_at.isoformat() if vr else None,
            },
            "summary": f"Report {report.id} ({report.event_type}) is {report.status} with verification outcome '{verification_status}' (credibility: {credibility_score if credibility_score is not None else 'N/A'}).",
        }

    # Query reports by location name
    res = resolve_location(db, location_name)
    if not res["success"]:
        return {
            "status": res["status"],
            "query": location_name,
            "found": False,
            "message": res["message"],
            **({"candidates": res["candidates"]} if "candidates" in res else {}),
        }

    loc = res["location"]
    location_data = res["location_data"]

    reports, total = _get_verifications_for_location(db, loc.id, limit=10)
    if not reports or total == 0:
        return {
            "status": "no_reports",
            "query": location_name,
            "found": True,
            "location": location_data,
            "reports": [],
            "total": 0,
            "message": f"No citizen reports recorded for {loc.name}.",
        }

    likely_valid_count = sum(
        1 for r in reports if r["verification"]["verification_status"] == "likely_valid"
    )
    summary_text = (
        f"{total} citizen report(s) found for {loc.name}; "
        f"{likely_valid_count} verified as likely valid."
    )

    return {
        "status": "success",
        "query": location_name,
        "found": True,
        "location": location_data,
        "reports": reports,
        "total": total,
        "summary": summary_text,
    }


def resolve_temperature_forecast(
    db: Session,
    location_name: str,
) -> dict[str, Any]:
    """Internal helper to retrieve persisted temperature forecasts without retraining."""
    res = resolve_location(db, location_name)
    if not res["success"]:
        return {
            "status": res["status"],
            "query": location_name,
            "found": False,
            "message": res["message"],
            **({"candidates": res["candidates"]} if "candidates" in res else {}),
        }

    loc = res["location"]
    location_data = res["location_data"]

    forecast_data = _get_forecast(db, loc.name, loc.id)
    if forecast_data is None:
        return {
            "status": "no_forecast",
            "query": location_name,
            "found": True,
            "location": location_data,
            "message": f"No saved temperature forecasts found for {loc.name}.",
            "forecast": None,
        }

    stale_text = " (stale)" if forecast_data["is_stale"] else ""
    summary_text = (
        f"Predicted temperature for {loc.name} ({forecast_data['forecast_horizon_hours']}h horizon): "
        f"{forecast_data['predicted_temperature_c']}°C via {forecast_data['model_name']}{stale_text}."
    )

    return {
        "status": "success",
        "query": location_name,
        "found": True,
        "location": location_data,
        "forecast": forecast_data,
        "summary": summary_text,
    }


def resolve_evidence_based_briefing(
    db: Session,
    location_name: str,
) -> dict[str, Any]:
    """Internal helper to coordinate evidence across all domains into a voice-friendly briefing."""
    res = resolve_location(db, location_name)
    if not res["success"]:
        return {
            "status": res["status"],
            "query": location_name,
            "found": False,
            "message": res["message"],
            **({"candidates": res["candidates"]} if "candidates" in res else {}),
        }

    loc = res["location"]
    location_data = res["location_data"]

    # Retrieve all components safely, handling partial data gracefully
    try:
        obs_data = _get_latest_observation(db, loc.id)
    except Exception:
        obs_data = None

    try:
        events_data, events_total = _get_events(db, loc.id, limit=5)
    except Exception:
        events_data, events_total = [], 0

    try:
        forecast_data = _get_forecast(db, loc.name, loc.id)
    except Exception:
        forecast_data = None

    try:
        verifications_data, verifications_total = _get_verifications_for_location(
            db, loc.id, limit=5
        )
    except Exception:
        verifications_data, verifications_total = [], 0

    # Collect data gaps and uncertainties
    data_gaps: list[str] = []
    if obs_data is None:
        data_gaps.append("Active telemetry weather observation is currently unavailable.")
    if not events_data:
        data_gaps.append("No severe weather events or warnings are on record.")
    if forecast_data is None:
        data_gaps.append("Machine learning temperature forecast is unavailable.")
    elif forecast_data["is_stale"]:
        data_gaps.append(
            f"Temperature forecast is older than the {forecast_data['forecast_horizon_hours']}h horizon window."
        )
    if not verifications_data:
        data_gaps.append("No verified citizen weather reports are on record for this location.")

    # Build clear, voice-friendly narrative
    narrative_parts: list[str] = []

    # 1. Observation narrative
    if obs_data:
        cond_str = obs_data["condition"] or "recorded conditions"
        temp_str = f"{obs_data['temperature_c']} degrees Celsius" if obs_data["temperature_c"] is not None else "unavailable"
        hum_str = f"with {obs_data['humidity_pct']} percent humidity" if obs_data["humidity_pct"] is not None else ""
        narrative_parts.append(
            f"Currently in {loc.name}, weather observations report {cond_str} at {temp_str} {hum_str}.".strip()
        )
    else:
        narrative_parts.append(f"In {loc.name}, direct telemetry observations are not currently available.")

    # 2. Weather events narrative
    if events_data:
        top_events = [f"{e['severity']} {e['event_type']}" for e in events_data[:2]]
        narrative_parts.append(
            f"There {'is' if len(events_data) == 1 else 'are'} {len(events_data)} recorded weather event{'s' if len(events_data) > 1 else ''}, including {', and '.join(top_events)}."
        )
    else:
        narrative_parts.append("No severe weather events are currently active.")

    # 3. Forecast narrative
    if forecast_data:
        stale_clause = " (note: forecast is older than the prediction horizon)" if forecast_data["is_stale"] else ""
        narrative_parts.append(
            f"The {forecast_data['model_name']} model forecasts a temperature of {forecast_data['predicted_temperature_c']} degrees Celsius over the next {forecast_data['forecast_horizon_hours']} hours{stale_clause}."
        )

    # 4. Citizen verification narrative
    if verifications_data:
        valid_reports = sum(1 for v in verifications_data if v["verification"]["verification_status"] == "likely_valid")
        narrative_parts.append(
            f"Ground-truth citizen intelligence shows {len(verifications_data)} report{'s' if len(verifications_data) > 1 else ''}, with {valid_reports} confirmed likely valid."
        )

    voice_narrative = " ".join(narrative_parts)

    return {
        "status": "success",
        "query": location_name,
        "found": True,
        "location": location_data,
        "briefing_timestamp": datetime.now(timezone.utc).isoformat(),
        "observation": obs_data,
        "weather_events": {
            "items": events_data,
            "total": events_total,
        },
        "temperature_forecast": forecast_data,
        "citizen_verifications": {
            "items": verifications_data,
            "total": verifications_total,
        },
        "data_gaps": data_gaps,
        "voice_narrative": voice_narrative,
    }


# ============================================================================
# Registered MCP Tools (Public Tool Surface for Alexa+ & MCP Clients)
# ============================================================================

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


@mcp_server.tool()
def get_weather_events(location_name: str, limit: int = 5) -> dict[str, Any]:
    """Retrieve genuine recorded weather events (e.g. rainfall, heatwave) for a registered location.

    Args:
        location_name: Name of the city or weather station (e.g. 'Pune').
        limit: Maximum number of recent events to return (default: 5, max: 50).

    Returns:
        Structured list of recorded weather events including event type, severity, start/end times,
        confidence score, and detection source.
    """
    db = SessionLocal()
    try:
        return resolve_weather_events(db, location_name, limit)
    finally:
        db.close()


@mcp_server.tool()
def get_verification_status(
    location_name: str | None = None,
    report_id: str | None = None,
) -> dict[str, Any]:
    """Retrieve the recorded verification status of citizen weather reports without altering data.

    Args:
        location_name: Optional name of the location to view citizen report verifications for.
        report_id: Optional UUID string of a specific citizen report to inspect.

    Returns:
        Structured verification results including report status (pending/verified/suspicious),
        verification outcome (likely_valid/uncertain/likely_misleading), credibility score,
        and evidence reasoning. Omits sensitive user personal information.
    """
    db = SessionLocal()
    try:
        return resolve_verification_status(db, location_name, report_id)
    finally:
        db.close()


@mcp_server.tool()
def get_temperature_forecast(location_name: str) -> dict[str, Any]:
    """Retrieve existing saved temperature predictions and model forecasts for a location.

    Args:
        location_name: Name of the city or weather station (e.g. 'Pune').

    Returns:
        Structured forecast data including predicted temperature in Celsius, forecast horizon hours,
        model name, generation timestamp, validity window, and freshness metadata.
    """
    db = SessionLocal()
    try:
        return resolve_temperature_forecast(db, location_name)
    finally:
        db.close()


@mcp_server.tool()
def get_evidence_based_briefing(location_name: str) -> dict[str, Any]:
    """Retrieve a comprehensive evidence-based weather intelligence briefing coordinating observations,
    active events, ground-truth citizen verifications, and machine learning forecasts.

    Args:
        location_name: Name of the city or weather station (e.g. 'Pune').

    Returns:
        Multi-source weather briefing including telemetry observations, recorded weather events,
        citizen verification outcomes, ML temperature forecasts, uncertainty/data gap notes,
        and an Alexa-friendly voice narrative.
    """
    db = SessionLocal()
    try:
        return resolve_evidence_based_briefing(db, location_name)
    finally:
        db.close()


def get_mcp_app() -> MCPASGIProxy:
    """Return the Starlette ASGI application proxy for the WeatherSentinel MCP server.

    Mounts Streamable HTTP at /mcp with local DNS-rebinding protection enabled.
    """
    return mcp_proxy
