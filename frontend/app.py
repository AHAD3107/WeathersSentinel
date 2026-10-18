
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


async def get_forecast_summary():
    """Fetch aggregate forecast statistics."""
    return await get_json(
        "/api/v1/temperature-predictions/summary"
    )


async def get_forecasts(
    location: str | None = None,
    page: int = 1,
    page_size: int = 20,
):
    """Fetch and normalize paginated forecast records."""
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

    if isinstance(response, list):
        return {
            "items": response,
            "total": len(response),
        }

    raise ValueError("Unexpected forecast API response format")


async def get_backend_health():
    """Check the backend health endpoint."""
    return await get_json("/health/")
