# WeatherSentinel Frontend

Interactive NiceGUI frontend for the WeatherSentinel National Weather Intelligence, Verification & Analytics Platform.

## Architecture

The frontend is built using **NiceGUI** with dark-mode styling, responsive layouts, and interactive mapping via **Leaflet**:

- **Geospatial Intelligence Map (`/map` or `/geospatial`)**: Interactive Leaflet map displaying real atmospheric observation stations and detected weather events with severity-coded overlays.
- **Weather Event Monitoring (`/events`)**: Multi-hazard severe weather feed with severity breakdown and confidence metrics.
- **Citizen Verification Hub (`/verification`)**: Crowdsourced weather report verification against nearby station telemetry with credibility scoring.
- **Forecast Analytics (`/dashboard`)**: Random Forest temperature predictions, statistical summaries, and Plotly trends.
- **Platform Overview (`/`)**: Animated welcome page with subsystem navigation and radar globe.

## Quick Start (Windows PowerShell)

```powershell
# 1. Enter the frontend directory
cd frontend

# 2. Sync dependencies using uv
uv sync

# 3. Start the NiceGUI application
uv run python app.py
```

The application will start on **http://127.0.0.1:8081**.

## Configuration

Set the backend API URL in `.env`:

```env
WEATHERSENTINEL_API_URL=http://127.0.0.1:8000
```

## Running Automated Tests

```powershell
uv run pytest -v
```
