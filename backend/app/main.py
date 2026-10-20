from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.mcp import get_mcp_app, mcp_server
from app.routers.citizen_reports import router as citizen_reports_router
from app.routers.health import router as health_router
from app.routers.locations import router as locations_router
from app.routers.temperature_predictions import router as temperature_predictions_router
from app.routers.verification import router as verification_router
from app.routers.weather import router as weather_router
from app.routers.weather_events import router as weather_events_router

mcp_app = get_mcp_app()


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    # If the session manager has already run (e.g. across multiple test clients),
    # refresh the streamable_http_app to obtain a fresh session manager
    if mcp_server.session_manager._has_started:
        mcp_app.refresh()
    async with mcp_server.session_manager.run():
        yield


app = FastAPI(
    title="WeatherSentinel API",
    description="National Weather Intelligence & Verification Platform",
    version="0.1.0",
    lifespan=lifespan,
)


app.include_router(health_router)
app.include_router(locations_router)
app.include_router(weather_router)
app.include_router(weather_events_router)
app.include_router(citizen_reports_router)
app.include_router(verification_router)
app.include_router(temperature_predictions_router)


@app.get("/")
def root():
    return {"message": "WeatherSentinel API is running"}


# Mount MCP Streamable HTTP ASGI application
# The MCP Streamable HTTP endpoint is served at /mcp (e.g. http://127.0.0.1:8000/mcp)
# Mounting at "/" after all REST routers ensures existing routes take precedence
app.mount("/", mcp_app)