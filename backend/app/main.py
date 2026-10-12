from fastapi import FastAPI

from app.routers.health import router as health_router
from app.routers.weather import router as weather_router
from app.routers.weather_events import router as weather_events_router
from app.routers.citizen_reports import router as citizen_reports_router
from app.routers.verification import router as verification_router
from app.routers.temperature_predictions import router as temperature_predictions_router


app = FastAPI(
    title="WeatherSentinel API",
    description="National Weather Intelligence & Verification Platform",
    version="0.1.0",
)


app.include_router(health_router)
app.include_router(weather_router)
app.include_router(weather_events_router)
app.include_router(citizen_reports_router)
app.include_router(verification_router)
app.include_router(temperature_predictions_router)


@app.get("/")
def root():
    return {"message": "WeatherSentinel API is running"}