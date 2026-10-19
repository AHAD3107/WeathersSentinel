
"""HTTP client helpers for the WeatherSentinel API."""

import os

import httpx
from dotenv import load_dotenv

load_dotenv()

API_BASE_URL = os.getenv(
    "WEATHERSENTINEL_API_URL",
    "http://127.0.0.1:8000",
).rstrip("/")

TIMEOUT = httpx.Timeout(10.0, connect=3.0)


async def get_json(path: str, params: dict | None = None):
    """Fetch JSON from the WeatherSentinel API."""
    url = f"{API_BASE_URL}/{path.lstrip('/')}"

    async with httpx.AsyncClient(timeout=TIMEOUT) as client:
        response = await client.get(url, params=params)
        response.raise_for_status()
        return response.json()


async def post_json(path: str, json_data: dict | None = None):
    """Send a POST request with JSON to the WeatherSentinel API."""
    url = f"{API_BASE_URL}/{path.lstrip('/')}"

    async with httpx.AsyncClient(timeout=TIMEOUT) as client:
        response = await client.post(url, json=json_data)
        response.raise_for_status()
        return response.json()


async def get_forecast_summary():
    """Return aggregate forecast statistics."""
    return await get_json(
        "/api/v1/temperature-predictions/summary"
    )


async def get_forecasts(
    location: str | None = None,
    page: int = 1,
    page_size: int = 20,
):
    """Return forecast records as a normalized list."""
    params = {
        "page": page,
        "page_size": page_size,
    }

    if location and location.strip():
        params["location"] = location.strip()

    response = await get_json(
        "/api/v1/temperature-predictions/forecasts",
        params=params,
    )

    # The backend returns {"value": [...], "Count": 16}.
    if isinstance(response, dict):
        records = response.get("value", [])
        total = response.get("Count", len(records))

        return {
            "items": records,
            "total": total,
        }

    # Also support a plain-list response.
    if isinstance(response, list):
        return {
            "items": response,
            "total": len(response),
        }

    raise ValueError(
        "Unexpected forecast API response format."
    )


async def get_backend_health():
    """Check backend health."""
    return await get_json("/health/")


async def get_backend_status_detailed() -> dict:
    """Return backend health check result with round-trip latency in ms."""
    import time

    start_time = time.perf_counter()
    try:
        data = await get_backend_health()
        elapsed_ms = (time.perf_counter() - start_time) * 1000
        return {
            "online": True,
            "latency_ms": round(elapsed_ms, 1),
            "data": data,
            "error": None,
        }
    except Exception as exc:
        elapsed_ms = (time.perf_counter() - start_time) * 1000
        return {
            "online": False,
            "latency_ms": round(elapsed_ms, 1),
            "data": None,
            "error": str(exc),
        }


async def get_weather_observations(
    location_id: str | None = None,
    source: str | None = None,
    page: int = 1,
    page_size: int = 50,
) -> dict:
    """Fetch paginated weather observations from the backend API."""
    params: dict = {
        "page": page,
        "page_size": page_size,
    }
    if location_id and str(location_id).strip():
        params["location_id"] = str(location_id).strip()
    if source and source.strip():
        params["source"] = source.strip()

    response = await get_json("/api/v1/weather-observations/", params=params)

    if isinstance(response, dict):
        return {
            "items": response.get("items", []),
            "total": response.get("total", 0),
            "page": response.get("page", page),
            "page_size": response.get("page_size", page_size),
        }

    if isinstance(response, list):
        return {
            "items": response,
            "total": len(response),
            "page": page,
            "page_size": page_size,
        }

    raise ValueError("Unexpected weather observations API response format.")


async def get_weather_events(
    location_id: str | None = None,
    event_type: str | None = None,
    severity: str | None = None,
    page: int = 1,
    page_size: int = 50,
) -> dict:
    """Fetch paginated weather events from the backend API."""
    params: dict = {
        "page": page,
        "page_size": page_size,
    }
    if location_id and str(location_id).strip():
        params["location_id"] = str(location_id).strip()
    if event_type and event_type.strip():
        params["event_type"] = event_type.strip().lower()
    if severity and severity.strip():
        params["severity"] = severity.strip().lower()

    response = await get_json("/api/v1/weather-events/", params=params)

    if isinstance(response, dict):
        return {
            "items": response.get("items", []),
            "total": response.get("total", 0),
            "page": response.get("page", page),
            "page_size": response.get("page_size", page_size),
        }

    if isinstance(response, list):
        return {
            "items": response,
            "total": len(response),
            "page": page,
            "page_size": page_size,
        }

    raise ValueError("Unexpected weather events API response format.")


async def get_citizen_reports(
    user_id: str | None = None,
    location_id: str | None = None,
    event_type: str | None = None,
    status: str | None = None,
    page: int = 1,
    page_size: int = 50,
) -> dict:
    """Fetch paginated citizen reports from the backend API."""
    params: dict = {
        "page": page,
        "page_size": page_size,
    }
    if user_id and str(user_id).strip():
        params["user_id"] = str(user_id).strip()
    if location_id and str(location_id).strip():
        params["location_id"] = str(location_id).strip()
    if event_type and event_type.strip():
        params["event_type"] = event_type.strip().lower()
    if status and status.strip():
        params["status"] = status.strip().lower()

    response = await get_json("/api/v1/citizen-reports/", params=params)

    if isinstance(response, dict):
        return {
            "items": response.get("items", []),
            "total": response.get("total", 0),
            "page": response.get("page", page),
            "page_size": response.get("page_size", page_size),
        }

    if isinstance(response, list):
        return {
            "items": response,
            "total": len(response),
            "page": page,
            "page_size": page_size,
        }

    raise ValueError("Unexpected citizen reports API response format.")


ALLOWED_CITIZEN_EVENT_TYPES = [
    "rainfall",
    "thunderstorm",
    "flooding",
    "heatwave",
    "fog",
    "dust_storm",
    "strong_wind",
    "other",
]


async def get_locations() -> list[dict]:
    """Fetch all registered weather station locations from the backend."""
    try:
        data = await get_json("/api/v1/locations/")
        if isinstance(data, list):
            return data
        if isinstance(data, dict) and "items" in data:
            return data["items"]
    except Exception as exc:
        print(f"Notice: Failed to fetch /api/v1/locations: {exc}")

    # Fallback to extracting locations from observations if needed
    try:
        obs_res = await get_weather_observations(page=1, page_size=100)
        items = obs_res.get("items", [])
        loc_map = {}
        for item in items:
            lid = item.get("location_id")
            if lid and lid not in loc_map:
                loc_map[lid] = {
                    "id": str(lid),
                    "name": item.get("source", "Telemetry Station"),
                    "district": "Sensor Network",
                    "state": "Maharashtra",
                }
        if loc_map:
            return list(loc_map.values())
    except Exception:
        pass
    return []


async def create_citizen_report(report_data: dict) -> dict:
    """Submit and persist a new citizen weather observation report to the backend."""
    return await post_json("/api/v1/citizen-reports/", json_data=report_data)


def format_citizen_report_description(
    notes: str | None = None,
    measurements: dict | None = None,
) -> str:
    """Combine user observation narrative and sensor measurements into a formatted description."""
    parts = []
    clean_notes = (notes or "").strip()
    if clean_notes:
        parts.append(clean_notes)

    if measurements and isinstance(measurements, dict):
        measurement_tags = []
        if measurements.get("temperature") is not None:
            measurement_tags.append(f"Temp: {measurements['temperature']}°C")
        if measurements.get("rainfall") is not None:
            measurement_tags.append(f"Rain: {measurements['rainfall']} mm")
        if measurements.get("humidity") is not None:
            measurement_tags.append(f"Humidity: {measurements['humidity']}%")
        if measurements.get("wind_speed") is not None:
            measurement_tags.append(f"Wind: {measurements['wind_speed']} km/h")

        if measurement_tags:
            parts.append(f"[Observed Measurements: {', '.join(measurement_tags)}]")

    result = " ".join(parts).strip()
    return result if result else "Ground weather observation report."


def validate_citizen_report_submission(data: dict) -> tuple[bool, str | None]:
    """Validate citizen report submission payload against domain constraints.

    Returns:
        (True, None) if valid.
        (False, error_message) if invalid.
    """
    if not isinstance(data, dict):
        return False, "Report payload must be an object."

    # Location ID
    loc_id = data.get("location_id")
    if not loc_id or not str(loc_id).strip():
        return False, "Location / Weather Station is mandatory."

    # Event Type
    event_type = data.get("event_type")
    if not event_type or not str(event_type).strip():
        return False, "Weather condition / event type is mandatory."
    clean_type = str(event_type).strip().lower()
    if clean_type not in ALLOWED_CITIZEN_EVENT_TYPES:
        return (
            False,
            f"Invalid event type '{event_type}'. Must be one of: {', '.join(ALLOWED_CITIZEN_EVENT_TYPES)}.",
        )

    # Observation Timestamp
    reported_at = data.get("reported_at")
    if not reported_at or not str(reported_at).strip():
        return False, "Observation timestamp is mandatory."

    # Description
    desc = data.get("description")
    if not desc or len(str(desc).strip()) < 5:
        return (
            False,
            "Observation description / notes must contain at least 5 characters.",
        )

    # Optional measurements validation if present in dict
    measurements = data.get("measurements")
    if measurements and isinstance(measurements, dict):
        temp = measurements.get("temperature")
        if temp is not None:
            try:
                t = float(temp)
                if not (-60.0 <= t <= 70.0):
                    return False, f"Temperature {t}°C is outside realistic range (-60°C to +70°C)."
            except (ValueError, TypeError):
                return False, f"Temperature value '{temp}' must be a valid number."

        rain = measurements.get("rainfall")
        if rain is not None:
            try:
                r = float(rain)
                if r < 0.0 or r > 2000.0:
                    return False, f"Rainfall {r} mm is outside valid range (0 to 2000 mm)."
            except (ValueError, TypeError):
                return False, f"Rainfall value '{rain}' must be a valid number."

        hum = measurements.get("humidity")
        if hum is not None:
            try:
                h = float(hum)
                if not (0.0 <= h <= 100.0):
                    return False, f"Relative humidity {h}% must be between 0% and 100%."
            except (ValueError, TypeError):
                return False, f"Humidity value '{hum}' must be a valid number."

        wind = measurements.get("wind_speed")
        if wind is not None:
            try:
                w = float(wind)
                if w < 0.0 or w > 500.0:
                    return False, f"Wind speed {w} km/h is outside valid range (0 to 500 km/h)."
            except (ValueError, TypeError):
                return False, f"Wind speed value '{wind}' must be a valid number."

    return True, None


async def verify_citizen_report(report_id: str) -> dict:
    """Trigger backend verification for a specific citizen report."""
    clean_id = str(report_id).strip()
    return await post_json(f"/api/v1/citizen-reports/{clean_id}/verify")


def extract_observation_coordinates(record: dict) -> tuple[float, float] | None:
    """Safely extract valid (latitude, longitude) coordinates from a record.

    Coordinates are looked up in record['raw_data'] or top-level fields.
    Returns None if missing or non-finite. Never fabricates coordinates.
    """
    if not isinstance(record, dict):
        return None

    raw_data = record.get("raw_data")
    lat_val = None
    lon_val = None

    if isinstance(raw_data, dict):
        lat_val = raw_data.get("latitude")
        lon_val = raw_data.get("longitude")

    if lat_val is None or lon_val is None:
        lat_val = record.get("latitude", lat_val)
        lon_val = record.get("longitude", lon_val)

    if lat_val is None or lon_val is None:
        return None

    try:
        lat = float(lat_val)
        lon = float(lon_val)
        if -90.0 <= lat <= 90.0 and -180.0 <= lon <= 180.0:
            return (lat, lon)
    except (TypeError, ValueError):
        return None

    return None


def resolve_event_coordinates(
    event: dict,
    location_coordinates_map: dict[str, tuple[float, float]] | None = None,
) -> tuple[float, float] | None:
    """Resolve verifiable GPS coordinates for a weather event.

    Sources of coordinates (in strict priority order):
    1. Direct verifiable coordinates in event['raw_data'] or top-level ('latitude', 'longitude').
    2. Linked location coordinates from location_coordinates_map using event['location_id'].

    Returns:
        (latitude, longitude) as float tuple if valid and verifiable.
        None if coordinates are missing, out of range, non-finite, or unresolvable.
        NEVER assigns default, arbitrary, or fabricated coordinates.
    """
    if not isinstance(event, dict):
        return None

    # 1. Direct coordinates on event payload
    lat_val = None
    lon_val = None
    raw_data = event.get("raw_data")
    if isinstance(raw_data, dict):
        lat_val = raw_data.get("latitude")
        lon_val = raw_data.get("longitude")

    if lat_val is None or lon_val is None:
        lat_val = event.get("latitude", lat_val)
        lon_val = event.get("longitude", lon_val)

    if lat_val is not None and lon_val is not None:
        try:
            lat = float(lat_val)
            lon = float(lon_val)
            if -90.0 <= lat <= 90.0 and -180.0 <= lon <= 180.0:
                return (lat, lon)
        except (TypeError, ValueError):
            pass

    # 2. Linked location coordinates from verifiable telemetry
    loc_id = event.get("location_id")
    if loc_id and location_coordinates_map and isinstance(location_coordinates_map, dict):
        clean_loc_id = str(loc_id).strip()
        mapped = location_coordinates_map.get(clean_loc_id)
        if mapped and isinstance(mapped, (tuple, list)) and len(mapped) == 2:
            try:
                lat = float(mapped[0])
                lon = float(mapped[1])
                if -90.0 <= lat <= 90.0 and -180.0 <= lon <= 180.0:
                    return (lat, lon)
            except (TypeError, ValueError):
                pass

    return None


def get_event_location_resolution(
    event: dict,
    location_coordinates_map: dict[str, tuple[float, float]] | None = None,
) -> dict:
    """Determine location resolution status and explanation for an event.

    Returns:
        dict with keys:
        - is_mappable: bool
        - coordinates: tuple[float, float] | None
        - location_id: str | None
        - source_type: 'event_payload' | 'linked_telemetry' | 'unresolved' | 'invalid_range'
        - reason: Human-readable explanation of why event is or isn't mappable.
    """
    if not isinstance(event, dict):
        return {
            "is_mappable": False,
            "coordinates": None,
            "location_id": None,
            "source_type": "invalid_event",
            "reason": "Invalid event record structure.",
        }

    loc_id = event.get("location_id")
    clean_loc_id = str(loc_id).strip() if loc_id else None

    # Check direct coordinates first
    lat_val = None
    lon_val = None
    raw_data = event.get("raw_data")
    if isinstance(raw_data, dict):
        lat_val = raw_data.get("latitude")
        lon_val = raw_data.get("longitude")
    if lat_val is None or lon_val is None:
        lat_val = event.get("latitude", lat_val)
        lon_val = event.get("longitude", lon_val)

    if lat_val is not None and lon_val is not None:
        try:
            lat = float(lat_val)
            lon = float(lon_val)
            if -90.0 <= lat <= 90.0 and -180.0 <= lon <= 180.0:
                return {
                    "is_mappable": True,
                    "coordinates": (lat, lon),
                    "location_id": clean_loc_id,
                    "source_type": "event_payload",
                    "reason": f"Direct GPS coordinates ({lat:.4f}°, {lon:.4f}°) present in event payload.",
                }
            return {
                "is_mappable": False,
                "coordinates": None,
                "location_id": clean_loc_id,
                "source_type": "invalid_range",
                "reason": f"Event coordinates ({lat_val}, {lon_val}) exceed valid geographic range [-90..90, -180..180].",
            }
        except (TypeError, ValueError):
            return {
                "is_mappable": False,
                "coordinates": None,
                "location_id": clean_loc_id,
                "source_type": "invalid_range",
                "reason": f"Event coordinate values ({lat_val!r}, {lon_val!r}) cannot be parsed as numeric.",
            }

    # Check linked location mapping
    if clean_loc_id:
        if location_coordinates_map and clean_loc_id in location_coordinates_map:
            mapped = location_coordinates_map[clean_loc_id]
            if mapped and isinstance(mapped, (tuple, list)) and len(mapped) == 2:
                try:
                    lat = float(mapped[0])
                    lon = float(mapped[1])
                    if -90.0 <= lat <= 90.0 and -180.0 <= lon <= 180.0:
                        return {
                            "is_mappable": True,
                            "coordinates": (lat, lon),
                            "location_id": clean_loc_id,
                            "source_type": "linked_telemetry",
                            "reason": f"Coordinates ({lat:.4f}°, {lon:.4f}°) verified from linked location telemetry.",
                        }
                    return {
                        "is_mappable": False,
                        "coordinates": None,
                        "location_id": clean_loc_id,
                        "source_type": "invalid_range",
                        "reason": f"Linked coordinates for location ID '{clean_loc_id}' exceed valid geographic range.",
                    }
                except (TypeError, ValueError):
                    return {
                        "is_mappable": False,
                        "coordinates": None,
                        "location_id": clean_loc_id,
                        "source_type": "invalid_range",
                        "reason": f"Linked coordinates for location ID '{clean_loc_id}' are non-numeric.",
                    }
        return {
            "is_mappable": False,
            "coordinates": None,
            "location_id": clean_loc_id,
            "source_type": "unresolved",
            "reason": f"Location ID '{clean_loc_id}' lacks verified GPS coordinates in API response and linked telemetry.",
        }

    return {
        "is_mappable": False,
        "coordinates": None,
        "location_id": None,
        "source_type": "unresolved",
        "reason": "Event has no linked location reference or geographic coordinates.",
    }
