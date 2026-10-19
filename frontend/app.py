"""WeatherSentinel: National Weather Intelligence, Verification & Analytics Platform.

Frontend application built with NiceGUI providing:
- Interactive Geospatial Intelligence Dashboard with Leaflet mapping
- Weather Event Monitoring and Severity Analytics
- Citizen Weather Report Verification Hub
- Random Forest ML Temperature Forecast Analytics
- Live Backend & Pipeline Health Tracking
"""

from datetime import datetime
import html
import plotly.graph_objects as go
from nicegui import ui

from api.client import (
    ALLOWED_CITIZEN_EVENT_TYPES,
    create_citizen_report,
    extract_observation_coordinates,
    format_citizen_report_description,
    get_backend_health,
    get_backend_status_detailed,
    get_citizen_reports,
    get_event_location_resolution,
    get_forecast_summary,
    get_forecasts,
    get_locations,
    get_weather_events,
    get_weather_observations,
    resolve_event_coordinates,
    validate_citizen_report_submission,
    verify_citizen_report,
)


# ---------------------------------------------------------
# Design System & Styling
# ---------------------------------------------------------

CSS = """
<style>
    body {
        background: #08111f;
        color: #e5edf5;
        font-family: Inter, ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
        margin: 0;
        padding: 0;
    }

    .ws-page {
        min-height: 100vh;
        background:
            radial-gradient(ellipse at 85% 15%, rgba(14, 116, 144, 0.15), transparent 45%),
            radial-gradient(ellipse at 15% 85%, rgba(15, 23, 42, 0.7), transparent 50%),
            #08111f;
        color: #e5edf5;
    }

    .ws-muted { color: #94a3b8; }
    .ws-dim { color: #64748b; }

    .ws-card {
        background: rgba(16, 28, 43, 0.88) !important;
        border: 1px solid #223247;
        border-radius: 14px;
        color: #e5edf5 !important;
        box-shadow: 0 4px 20px -2px rgba(0, 0, 0, 0.45) !important;
        backdrop-filter: blur(8px);
    }

    .ws-card-interactive {
        transition: transform 0.2s ease, border-color 0.2s ease, box-shadow 0.2s ease;
    }

    .ws-card-interactive:hover {
        transform: translateY(-2px);
        border-color: #38bdf8;
        box-shadow: 0 8px 24px -4px rgba(56, 189, 248, 0.2) !important;
    }

    .ws-button {
        border-radius: 9px;
        font-weight: 600;
        text-transform: none;
        letter-spacing: 0.01em;
    }

    .ws-btn-primary {
        background: #0e7490 !important;
        color: #ffffff !important;
        border: 1px solid rgba(56, 189, 248, 0.4) !important;
        transition: all 0.2s ease !important;
    }

    .ws-btn-primary:hover {
        background: #0284c7 !important;
        border-color: #38bdf8 !important;
        box-shadow: 0 4px 14px rgba(14, 116, 144, 0.4) !important;
        transform: translateY(-1px);
    }

    .ws-btn-secondary {
        background: #1e293b !important;
        color: #e2e8f0 !important;
        border: 1px solid #334155 !important;
    }

    .ws-btn-secondary:hover {
        background: #334155 !important;
        border-color: #64748b !important;
    }

    /* Badges & Pills */
    .ws-pill {
        display: inline-flex;
        align-items: center;
        gap: 0.35rem;
        padding: 0.2rem 0.65rem;
        border-radius: 9999px;
        font-size: 0.75rem;
        font-weight: 600;
        text-transform: uppercase;
        letter-spacing: 0.04em;
    }

    .ws-pill-cyan {
        background: rgba(6, 182, 212, 0.15);
        color: #22d3ee;
        border: 1px solid rgba(34, 211, 238, 0.35);
    }

    .ws-pill-emerald {
        background: rgba(16, 185, 129, 0.15);
        color: #34d399;
        border: 1px solid rgba(52, 211, 153, 0.35);
    }

    .ws-pill-amber {
        background: rgba(245, 158, 11, 0.15);
        color: #fbbf24;
        border: 1px solid rgba(251, 191, 36, 0.35);
    }

    .ws-pill-rose {
        background: rgba(244, 63, 94, 0.15);
        color: #fb7185;
        border: 1px solid rgba(251, 113, 133, 0.35);
    }

    .ws-pill-purple {
        background: rgba(168, 85, 247, 0.15);
        color: #c084fc;
        border: 1px solid rgba(192, 132, 252, 0.35);
    }

    /* Radar / Globe Styles */
    .ws-globe-wrap {
        position: relative;
        width: min(76vw, 360px);
        aspect-ratio: 1;
        display: grid;
        place-items: center;
        margin: auto;
        isolation: isolate;
    }

    .ws-globe {
        position: relative;
        width: 72%;
        aspect-ratio: 1;
        border-radius: 50%;
        overflow: hidden;
        background:
            radial-gradient(circle at 32% 27%, #28627e 0%,
                #15394f 32%, #0a2034 67%, #071421 100%);
        box-shadow:
            inset -18px -12px 35px rgba(0, 0, 0, .55),
            inset 8px 5px 25px rgba(103, 232, 249, .12),
            0 0 36px rgba(56, 189, 248, .18);
        border: 1px solid rgba(125, 211, 252, .48);
    }

    .ws-globe-grid {
        position: absolute;
        inset: -18%;
        border-radius: 50%;
        opacity: .55;
        background:
            repeating-linear-gradient(90deg,
                transparent 0px, transparent 25px,
                rgba(103, 232, 249, .27) 26px,
                transparent 27px, transparent 49px),
            repeating-linear-gradient(0deg,
                transparent 0px, transparent 25px,
                rgba(103, 232, 249, .20) 26px,
                transparent 27px, transparent 49px);
        animation: ws-globe-rotate 42s linear infinite;
    }

    .ws-globe-sweep {
        position: absolute;
        inset: -5%;
        border-radius: 50%;
        background: conic-gradient(from 0deg,
            transparent 0deg, transparent 270deg,
            rgba(34, 211, 238, .02) 310deg,
            rgba(34, 211, 238, .28) 350deg, transparent 360deg);
        animation: ws-radar 8s linear infinite;
    }

    .ws-globe::after {
        content: "";
        position: absolute;
        inset: 0;
        border-radius: 50%;
        box-shadow: inset -18px -5px 25px rgba(0, 0, 0, .36);
        background: radial-gradient(circle at 30% 28%,
            transparent 25%, rgba(3, 10, 20, .35) 100%);
        pointer-events: none;
    }

    .ws-orbit {
        position: absolute;
        width: 100%;
        height: 37%;
        border: 1px solid rgba(103, 232, 249, .43);
        border-radius: 50%;
        transform: rotate(-27deg);
        pointer-events: none;
    }

    .ws-orbit-two {
        width: 94%;
        height: 58%;
        transform: rotate(48deg);
        border-color: rgba(56, 189, 248, .22);
    }

    .ws-status-dot {
        display: inline-block;
        height: 8px;
        width: 8px;
        border-radius: 50%;
        background: #22d3ee;
        box-shadow: 0 0 10px #22d3ee;
    }

    .ws-status-dot-green {
        background: #10b981;
        box-shadow: 0 0 10px #10b981;
    }

    .ws-status-dot-red {
        background: #ef4444;
        box-shadow: 0 0 10px #ef4444;
    }

    /* Leaflet customization for dark theme */
    .leaflet-container {
        background: #09121d !important;
        font-family: inherit !important;
        border-radius: 12px;
        z-index: 10;
    }

    .leaflet-tile {
        filter: brightness(0.85) contrast(1.15) saturate(1.1);
    }

    .leaflet-popup-content-wrapper {
        background: #0f1d2e !important;
        color: #e5edf5 !important;
        border: 1px solid #223247 !important;
        border-radius: 10px !important;
        box-shadow: 0 12px 30px -4px rgba(0, 0, 0, 0.7) !important;
    }

    .leaflet-popup-tip {
        background: #0f1d2e !important;
    }

    .leaflet-popup-content {
        margin: 12px 14px !important;
        line-height: 1.5 !important;
    }

    .leaflet-bar a {
        background-color: #101c2b !important;
        color: #e5edf5 !important;
        border-bottom: 1px solid #223247 !important;
    }

    .leaflet-bar a:hover {
        background-color: #1a2c42 !important;
        color: #38bdf8 !important;
    }

    /* Quasar overrides for input controls */
    .q-field__label { color: #94a3b8 !important; }
    .q-field__native, .q-field__input { color: #e5edf5 !important; }
    .q-field--outlined .q-field__control:before { border-color: #223247 !important; }
    .q-field--outlined:hover .q-field__control:before { border-color: #38bdf8 !important; }
    .q-table__container { background: transparent !important; color: #e5edf5 !important; }
    .q-table th { color: #94a3b8 !important; font-weight: 600 !important; }
    .q-table tbody tr { border-bottom: 1px solid #1a2736 !important; }
    .q-table tbody tr:hover { background: rgba(56, 189, 248, 0.05) !important; }

    @keyframes ws-globe-rotate {
        from { transform: rotate(0deg); }
        to { transform: rotate(360deg); }
    }

    @keyframes ws-radar {
        from { transform: rotate(0deg); }
        to { transform: rotate(360deg); }
    }

    @keyframes ws-fade-up {
        from { opacity: 0; transform: translateY(8px); }
        to { opacity: 1; transform: translateY(0); }
    }

    .ws-animate-1 { animation: ws-fade-up 0.5s cubic-bezier(0.16, 1, 0.3, 1) both 0.05s; }
    .ws-animate-2 { animation: ws-fade-up 0.55s cubic-bezier(0.16, 1, 0.3, 1) both 0.12s; }
    .ws-animate-3 { animation: ws-fade-up 0.6s cubic-bezier(0.16, 1, 0.3, 1) both 0.20s; }
    .ws-animate-4 { animation: ws-fade-up 0.65s cubic-bezier(0.16, 1, 0.3, 1) both 0.28s; }

    /* Hero layout */
    .ws-hero {
        display: flex;
        flex-direction: row;
        align-items: center;
        gap: 3rem;
        width: 100%;
        max-width: 1200px;
        margin: 0 auto;
        padding: 3.5rem 0 3rem;
    }

    .ws-hero-text {
        flex: 0 0 55%;
        min-width: 0;
        display: flex;
        flex-direction: column;
        gap: 1.25rem;
    }

    .ws-hero-globe {
        flex: 0 0 45%;
        min-width: 0;
        display: flex;
        flex-direction: column;
        align-items: center;
        justify-content: center;
        gap: 1.25rem;
    }

    @media (max-width: 860px) {
        .ws-hero {
            flex-direction: column;
            padding: 2rem 0;
            gap: 2rem;
        }
        .ws-hero-text, .ws-hero-globe {
            flex: 0 0 auto;
            width: 100%;
        }
    }
</style>
"""


def configure_page(title: str) -> None:
    """Configure the current page with theme colors and stylesheets."""
    ui.colors(
        primary="#38bdf8",
        secondary="#0f172a",
        accent="#22d3ee",
        positive="#10b981",
        warning="#f59e0b",
        negative="#ef4444",
    )
    ui.page_title(title)
    ui.add_head_html(CSS)


# ---------------------------------------------------------
# Formatting and Value Helpers
# ---------------------------------------------------------

def format_temperature(value) -> str:
    """Format temperature value in Celsius."""
    if value is None:
        return "—"
    try:
        return f"{float(value):.2f} °C"
    except (TypeError, ValueError):
        return "—"


def format_metric(value, unit: str = "") -> str:
    """Format numeric telemetry measurement with unit."""
    if value is None:
        return "—"
    try:
        num = float(value)
        return f"{num:.2f} {unit}".strip()
    except (TypeError, ValueError):
        return str(value)


def format_timestamp(value) -> str:
    """Format an ISO timestamp to readable UTC date and time."""
    if not value:
        return "Unknown"
    try:
        timestamp = datetime.fromisoformat(
            str(value).replace("Z", "+00:00")
        )
        return timestamp.strftime("%d %b %Y, %H:%M UTC")
    except (TypeError, ValueError):
        return str(value)


def get_severity_badge_class(severity: str) -> str:
    """Return styling class for weather event severity."""
    s = (severity or "").lower()
    if s == "extreme":
        return "ws-pill ws-pill-rose"
    if s == "high":
        return "ws-pill ws-pill-amber"
    if s == "medium":
        return "ws-pill ws-pill-cyan"
    return "ws-pill ws-pill-emerald"


def get_status_badge_class(status: str) -> str:
    """Return styling class for verification or report status."""
    st = (status or "").lower()
    if st in {"verified", "likely_valid"}:
        return "ws-pill ws-pill-emerald"
    if st in {"suspicious", "likely_misleading"}:
        return "ws-pill ws-pill-rose"
    if st in {"pending", "uncertain"}:
        return "ws-pill ws-pill-amber"
    return "ws-pill ws-pill-purple"


# ---------------------------------------------------------
# Shared Navigation Header & Health Indicator
# ---------------------------------------------------------

def render_navigation_header(active_route: str = "/"):
    """Render the standard responsive top navigation bar with live health."""
    with ui.row().classes(
        "w-full max-w-7xl mx-auto items-center justify-between gap-4 py-4 px-2 flex-wrap"
    ):
        # Brand logo
        with ui.row().classes("items-center gap-3 cursor-pointer").on(
            "click", lambda: ui.navigate.to("/")
        ):
            with ui.element("div").classes(
                "rounded-xl p-2.5 border border-cyan-800"
            ).style("background: rgba(14, 116, 144, 0.2)"):
                ui.icon("radar", size="sm").style("color: #38bdf8")

            with ui.column().classes("gap-0"):
                ui.label("WeatherSentinel").classes("text-lg font-bold tracking-tight text-white")
                ui.label("NATIONAL WEATHER PLATFORM").classes(
                    "text-[10px] tracking-widest font-semibold ws-muted"
                )

        # Nav links
        with ui.row().classes("items-center gap-1 sm:gap-2 flex-wrap"):
            nav_items = [
                ("/", "Welcome", "home"),
                ("/map", "Geospatial Map", "map"),
                ("/dashboard", "Forecasts", "show_chart"),
                ("/events", "Events", "warning"),
                ("/verification", "Verification", "verified_user"),
            ]

            for route, label, icon in nav_items:
                is_active = active_route == route or (route == "/map" and active_route == "/geospatial")
                btn_classes = "ws-button px-3 py-1.5 text-xs sm:text-sm "
                if is_active:
                    btn_classes += "ws-btn-primary"
                    props = "unelevated"
                else:
                    btn_classes += "text-slate-300 hover:text-white"
                    props = "flat"

                ui.button(
                    label,
                    icon=icon,
                    on_click=lambda r=route: ui.navigate.to(r),
                ).props(props).classes(btn_classes)

        # Health indicator pill
        with ui.row().classes(
            "items-center gap-2 px-3 py-1 rounded-full border border-slate-700 text-xs"
        ).style("background: rgba(15, 23, 42, 0.6)"):
            health_dot = ui.html(
                '<span class="ws-status-dot ws-status-dot-green"></span>',
                sanitize=False,
            )
            health_label = ui.label("API: Checking...").classes("text-xs font-medium")

        async def check_health():
            res = await get_backend_status_detailed()
            if res.get("online"):
                health_dot.content = '<span class="ws-status-dot ws-status-dot-green"></span>'
                ms = res.get("latency_ms", 0)
                health_label.text = f"API Online ({ms:.0f}ms)"
                health_label.classes("text-emerald-400", remove="text-rose-400 text-amber-400")
            else:
                health_dot.content = '<span class="ws-status-dot ws-status-dot-red"></span>'
                health_label.text = "API Offline"
                health_label.classes("text-rose-400", remove="text-emerald-400 text-amber-400")

        ui.timer(0.1, check_health, once=True)

    ui.separator().classes("w-full max-w-7xl mx-auto mb-6").style("background: #1e293b")


# ---------------------------------------------------------
# Page 1: Welcome Page
# ---------------------------------------------------------

@ui.page("/")
def welcome_page():
    """Render WeatherSentinel platform welcome hub."""
    configure_page("WeatherSentinel | National Weather Intelligence Platform")

    with ui.column().classes("ws-page w-full px-4 sm:px-6 py-4"):
        render_navigation_header("/")

        with ui.element("div").classes("ws-hero"):
            with ui.element("div").classes("ws-hero-text"):
                ui.label(
                    "NATIONAL WEATHER INTELLIGENCE & VERIFICATION"
                ).classes("text-xs font-semibold tracking-widest ws-animate-1").style("color: #38bdf8")

                ui.label(
                    "Weather Data.\nVerified Decisions."
                ).classes("text-4xl sm:text-5xl font-extrabold leading-tight text-white ws-animate-2").style(
                    "white-space: pre-line; letter-spacing: -0.03em"
                )

                ui.label(
                    "Real-time observation ingestion, severe weather event detection, "
                    "crowdsourced ground verification, and ML temperature forecasting."
                ).classes("text-base sm:text-lg leading-relaxed ws-muted ws-animate-3")

                with ui.row().classes("gap-3 flex-wrap items-center ws-animate-4 pt-2"):
                    ui.button(
                        "Launch Geospatial Map",
                        icon="explore",
                        on_click=lambda: ui.navigate.to("/map"),
                    ).props("unelevated").classes("ws-button ws-btn-primary px-5 py-2.5")

                    ui.button(
                        "Forecast Analytics",
                        icon="insights",
                        on_click=lambda: ui.navigate.to("/dashboard"),
                    ).props("flat").classes("ws-button ws-btn-secondary px-5 py-2.5")

            with ui.element("div").classes("ws-hero-globe"):
                ui.html("""
                    <div class="ws-globe-wrap" role="img" aria-label="WeatherSentinel Atmospheric Globe">
                        <div class="ws-orbit"></div>
                        <div class="ws-orbit ws-orbit-two"></div>
                        <div class="ws-globe">
                            <div class="ws-globe-grid"></div>
                            <div class="ws-globe-sweep"></div>
                        </div>
                    </div>
                """, sanitize=False)
                ui.label("REAL-TIME SPATIAL SENSING & FORECASTING").classes(
                    "text-[11px] tracking-widest ws-dim font-medium text-center"
                )

        # 4 Core System Capability Cards
        ui.separator().classes("w-full max-w-7xl mx-auto my-6").style("background: #1e293b")

        with ui.column().classes("w-full max-w-7xl mx-auto gap-4 pb-12"):
            ui.label("Platform Core Capabilities").classes("text-xl font-bold text-white")
            ui.label(
                "Explore the specialized intelligence modules integrated into WeatherSentinel."
            ).classes("text-sm ws-muted mb-2")

            with ui.row().classes("w-full gap-5 items-stretch flex-wrap"):
                # Card 1: Geospatial Intelligence
                with ui.card().classes("ws-card ws-card-interactive flex-grow p-6 cursor-pointer").style(
                    "flex-basis: calc(50% - 1.25rem); min-width: 290px"
                ).on("click", lambda: ui.navigate.to("/map")):
                    with ui.row().classes("items-center justify-between w-full mb-3"):
                        with ui.element("div").classes("p-3 rounded-lg border border-cyan-800").style("background: rgba(6, 182, 212, 0.15)"):
                            ui.icon("public", size="md").style("color: #22d3ee")
                        ui.label("INTERACTIVE GIS").classes("ws-pill ws-pill-cyan")
                    ui.label("Geospatial Intelligence Map").classes("text-lg font-bold text-white mb-1")
                    ui.label(
                        "Live geospatial visualization of atmospheric observations and detected events on Leaflet GIS."
                    ).classes("text-sm ws-muted leading-relaxed")
                    ui.link("Open GIS Dashboard →", "/map").classes("text-xs text-cyan-400 font-semibold mt-4")

                # Card 2: Forecast Analytics
                with ui.card().classes("ws-card ws-card-interactive flex-grow p-6 cursor-pointer").style(
                    "flex-basis: calc(50% - 1.25rem); min-width: 290px"
                ).on("click", lambda: ui.navigate.to("/dashboard")):
                    with ui.row().classes("items-center justify-between w-full mb-3"):
                        with ui.element("div").classes("p-3 rounded-lg border border-blue-800").style("background: rgba(59, 130, 246, 0.15)"):
                            ui.icon("trending_up", size="md").style("color: #60a5fa")
                        ui.label("MACHINE LEARNING").classes("ws-pill ws-pill-cyan")
                    ui.label("Temperature Forecast Analytics").classes("text-lg font-bold text-white mb-1")
                    ui.label(
                        "Random Forest temperature forecasting model metrics, aggregate statistics, and interactive trends."
                    ).classes("text-sm ws-muted leading-relaxed")
                    ui.link("Explore Forecasts →", "/dashboard").classes("text-xs text-sky-400 font-semibold mt-4")

                # Card 3: Weather Event Monitoring
                with ui.card().classes("ws-card ws-card-interactive flex-grow p-6 cursor-pointer").style(
                    "flex-basis: calc(50% - 1.25rem); min-width: 290px"
                ).on("click", lambda: ui.navigate.to("/events")):
                    with ui.row().classes("items-center justify-between w-full mb-3"):
                        with ui.element("div").classes("p-3 rounded-lg border border-amber-800").style("background: rgba(245, 158, 11, 0.15)"):
                            ui.icon("bolt", size="md").style("color: #fbbf24")
                        ui.label("HAZARD MONITOR").classes("ws-pill ws-pill-amber")
                    ui.label("Severe Weather Event Detection").classes("text-lg font-bold text-white mb-1")
                    ui.label(
                        "Automated rule-based and sensor-derived hazard detection for rainfall, heatwaves, and storms with severity scoring."
                    ).classes("text-sm ws-muted leading-relaxed")
                    ui.link("View Active Events →", "/events").classes("text-xs text-amber-400 font-semibold mt-4")

                # Card 4: Citizen Verification Hub
                with ui.card().classes("ws-card ws-card-interactive flex-grow p-6 cursor-pointer").style(
                    "flex-basis: calc(50% - 1.25rem); min-width: 290px"
                ).on("click", lambda: ui.navigate.to("/verification")):
                    with ui.row().classes("items-center justify-between w-full mb-3"):
                        with ui.element("div").classes("p-3 rounded-lg border border-emerald-800").style("background: rgba(16, 185, 129, 0.15)"):
                            ui.icon("verified", size="md").style("color: #34d399")
                        ui.label("CROWD VERIFICATION").classes("ws-pill ws-pill-emerald")
                    ui.label("Citizen Report Verification Hub").classes("text-lg font-bold text-white mb-1")
                    ui.label(
                        "Automated credibility assessment of crowdsourced citizen weather reports against nearby station telemetry."
                    ).classes("text-sm ws-muted leading-relaxed")
                    ui.link("Run Report Verification →", "/verification").classes("text-xs text-emerald-400 font-semibold mt-4")


# ---------------------------------------------------------
# Page 2: Primary Implementation — Geospatial Dashboard
# ---------------------------------------------------------

@ui.page("/map")
@ui.page("/geospatial")
async def geospatial_dashboard_page():
    """Render interactive Geospatial Intelligence Dashboard with Leaflet."""
    configure_page("WeatherSentinel | Geospatial Intelligence Dashboard")

    active_observation_layers = []
    active_event_layers = []
    selected_record = {"data": None, "type": None}

    # Center map on default coordinates (Pune, Maharashtra, India)
    DEFAULT_CENTER = (18.5204, 73.8567)
    DEFAULT_ZOOM = 12

    with ui.column().classes("ws-page w-full px-4 sm:px-6 py-4"):
        render_navigation_header("/map")

        # Top section: Header & Quick Stats
        with ui.row().classes("w-full max-w-7xl mx-auto items-center justify-between gap-4 flex-wrap mb-4"):
            with ui.column().classes("gap-0"):
                ui.label("Geospatial Intelligence Dashboard").classes("text-2xl font-extrabold text-white")
                ui.label("Interactive spatial telemetry map and weather event overlay").classes("text-sm ws-muted")

            with ui.row().classes("items-center gap-2 flex-wrap"):
                reset_view_btn = ui.button(
                    "Reset View",
                    icon="my_location",
                ).props("flat").classes("ws-button ws-btn-secondary text-xs sm:text-sm")

                refresh_btn = ui.button(
                    "Refresh GIS Data",
                    icon="refresh",
                ).props("unelevated").classes("ws-button ws-btn-primary text-xs sm:text-sm")

        # KPI Summary Cards
        with ui.row().classes("w-full max-w-7xl mx-auto gap-4 flex-wrap mb-5"):
            with ui.card().classes("ws-card flex-grow p-4").style("min-width: 160px"):
                ui.label("Total Observations").classes("text-xs ws-muted uppercase tracking-wider")
                total_obs_label = ui.label("—").classes("text-2xl font-bold text-white")

            with ui.card().classes("ws-card flex-grow p-4").style("min-width: 160px"):
                ui.label("Plotted Observations (GPS)").classes("text-xs ws-muted uppercase tracking-wider")
                geocoded_label = ui.label("—").classes("text-2xl font-bold text-cyan-400")

            with ui.card().classes("ws-card flex-grow p-4").style("min-width: 160px"):
                ui.label("Detected Events").classes("text-xs ws-muted uppercase tracking-wider")
                total_events_label = ui.label("—").classes("text-2xl font-bold text-amber-400")

            with ui.card().classes("ws-card flex-grow p-4").style("min-width: 180px"):
                ui.label("Event Map Status").classes("text-xs ws-muted uppercase tracking-wider")
                events_map_status_label = ui.label("—").classes("text-lg font-bold text-white")

            with ui.card().classes("ws-card flex-grow p-4").style("min-width: 160px"):
                ui.label("Current Status").classes("text-xs ws-muted uppercase tracking-wider")
                status_kpi_label = ui.label("Syncing...").classes("text-base font-semibold text-emerald-400")

        # Filter Toolbar
        with ui.card().classes("w-full max-w-7xl mx-auto ws-card p-4 mb-5"):
            with ui.row().classes("w-full items-center justify-between gap-3 flex-wrap"):
                with ui.row().classes("items-center gap-3 flex-wrap flex-grow"):
                    source_filter = ui.select(
                        options=["All", "OPEN_METEO", "NOAA_ISD_LITE"],
                        value="All",
                        label="Observation Source",
                    ).props("outlined dense").classes("w-44 text-xs")

                    event_type_filter = ui.select(
                        options=["All", "rainfall", "heatwave", "thunderstorm", "flooding", "fog", "other"],
                        value="All",
                        label="Event Type",
                    ).props("outlined dense").classes("w-44 text-xs")

                    severity_filter = ui.select(
                        options=["All", "extreme", "high", "medium", "low"],
                        value="All",
                        label="Event Severity",
                    ).props("outlined dense").classes("w-40 text-xs")

                    apply_filter_btn = ui.button(
                        "Apply Filters",
                        icon="filter_alt",
                    ).props("unelevated").classes("ws-button ws-btn-primary text-xs px-4 py-2")

                    reset_filter_btn = ui.button(
                        "Clear",
                        icon="clear",
                    ).props("flat").classes("ws-button ws-btn-secondary text-xs px-3 py-2")

                with ui.row().classes("items-center gap-2"):
                    show_obs_toggle = ui.checkbox("Observations", value=True).classes("text-xs text-cyan-300")
                    show_events_toggle = ui.checkbox("Weather Events", value=True).classes("text-xs text-amber-300")

        # Data Model Disclaimer & Schema Note
        with ui.element("div").classes(
            "w-full max-w-7xl mx-auto mb-4 px-4 py-2.5 rounded-lg border border-cyan-900 flex items-center justify-between gap-3"
        ).style("background: rgba(14, 116, 144, 0.12)"):
            with ui.row().classes("items-center gap-2"):
                ui.icon("verified_user", size="sm").style("color: #38bdf8")
                ui.label(
                    "Geospatial Integrity Policy: Map markers are placed strictly at verifiable GPS coordinates. "
                    "Events without verifiable coordinates are listed in the Hazard Feed with their omission rationale; "
                    "markers are never assigned arbitrary or fallback positions."
                ).classes("text-xs ws-muted")

        # Main Workspace: Map on Left (70%) + Inspector Card on Right (30%)
        with ui.row().classes("w-full max-w-7xl mx-auto gap-5 items-stretch flex-wrap"):
            # Map Container
            with ui.column().classes("flex-grow").style("flex-basis: 62%; min-width: 320px"):
                with ui.card().classes("ws-card w-full p-2 relative").style("min-height: 520px"):
                    map_instance = ui.leaflet(
                        center=DEFAULT_CENTER,
                        zoom=DEFAULT_ZOOM,
                    ).classes("w-full rounded-lg").style("height: 560px")

                    # Map Overlay Legend
                    with ui.element("div").classes(
                        "absolute bottom-4 left-4 z-20 px-3 py-2 rounded-lg border border-slate-700 pointer-events-none"
                    ).style("background: rgba(15, 23, 42, 0.85); backdrop-filter: blur(6px)"):
                        with ui.column().classes("gap-1 text-[11px]"):
                            ui.label("GIS Map Legend").classes("font-semibold text-white")
                            with ui.row().classes("items-center gap-1.5"):
                                ui.html('<span style="display:inline-block; width:10px; height:10px; border-radius:50%; background:#0284c7; border:2px solid #38bdf8"></span>', sanitize=False)
                                ui.label("Weather Observation").classes("ws-muted")
                            with ui.row().classes("items-center gap-1.5"):
                                ui.html('<span style="display:inline-block; width:10px; height:10px; border-radius:50%; background:#ef4444"></span>', sanitize=False)
                                ui.label("Extreme/High Event").classes("ws-muted")
                            with ui.row().classes("items-center gap-1.5"):
                                ui.html('<span style="display:inline-block; width:10px; height:10px; border-radius:50%; background:#f59e0b"></span>', sanitize=False)
                                ui.label("Medium/Low Event").classes("ws-muted")

            # Inspector & Telemetry Panel (Right Side)
            with ui.column().classes("flex-grow").style("flex-basis: 34%; min-width: 300px"):
                with ui.card().classes("ws-card w-full p-5 flex flex-col gap-4").style("height: 576px"):
                    with ui.row().classes("items-center justify-between w-full border-b border-slate-700 pb-2"):
                        ui.label("Selected Telemetry Inspector").classes("text-base font-bold text-white")
                        inspector_badge = ui.label("No selection").classes("ws-pill ws-pill-cyan")

                    # Inspector dynamic content container
                    inspector_container = ui.column().classes("w-full gap-3 overflow-y-auto flex-grow")

                    with inspector_container:
                        ui.label("Select a map marker or feed record below to inspect atmospheric telemetry.").classes(
                            "text-xs ws-muted leading-relaxed"
                        )
                        with ui.card().classes("w-full p-3 rounded-lg border border-slate-800").style("background: rgba(15, 23, 42, 0.4)"):
                            ui.label("Tip: Click any marker or table row to view instant telemetry details.").classes("text-xs ws-dim")

        # Telemetry & Event Records Section
        with ui.column().classes("w-full max-w-7xl mx-auto mt-6 gap-3 pb-12"):
            with ui.row().classes("w-full items-center justify-between gap-3 flex-wrap"):
                with ui.column().classes("gap-0"):
                    ui.label("Geospatial Telemetry & Hazard Feeds").classes("text-lg font-bold text-white")
                    table_status_label = ui.label("Showing latest records").classes("text-xs ws-muted")

            with ui.tabs().classes("w-full border-b border-slate-700") as data_tabs:
                obs_tab = ui.tab("Atmospheric Observations Telemetry", icon="thermostat")
                events_tab = ui.tab("Detected Weather Events Feed", icon="bolt")

            with ui.tab_panels(data_tabs, value=obs_tab).classes("w-full bg-transparent p-0"):
                with ui.tab_panel(obs_tab).classes("p-0 pt-3"):
                    obs_table = ui.table(
                        columns=[
                            {"name": "observed_at", "label": "Observed At (UTC)", "field": "observed_at", "align": "left", "sortable": True},
                            {"name": "source", "label": "Source", "field": "source", "align": "left"},
                            {"name": "temperature", "label": "Temp (°C)", "field": "temperature", "align": "right"},
                            {"name": "humidity", "label": "Humidity", "field": "humidity", "align": "right"},
                            {"name": "pressure", "label": "Pressure", "field": "pressure", "align": "right"},
                            {"name": "rainfall", "label": "Rainfall", "field": "rainfall", "align": "right"},
                            {"name": "wind", "label": "Wind (m/s)", "field": "wind", "align": "right"},
                            {"name": "coordinates", "label": "GPS Status", "field": "coordinates", "align": "center"},
                            {"name": "condition", "label": "Condition", "field": "condition", "align": "left"},
                        ],
                        rows=[],
                        row_key="id",
                        pagination={"rowsPerPage": 10},
                    ).classes("w-full ws-card")

                with ui.tab_panel(events_tab).classes("p-0 pt-3"):
                    events_table = ui.table(
                        columns=[
                            {"name": "event_type", "label": "Hazard Event", "field": "event_type", "align": "left", "sortable": True},
                            {"name": "severity", "label": "Severity", "field": "severity", "align": "center"},
                            {"name": "confidence", "label": "Confidence", "field": "confidence", "align": "right"},
                            {"name": "start_time", "label": "Detection Time", "field": "start_time", "align": "left"},
                            {"name": "map_status", "label": "Map Position Status", "field": "map_status", "align": "center"},
                            {"name": "reason", "label": "Geospatial Integrity & Resolution Details", "field": "reason", "align": "left"},
                        ],
                        rows=[],
                        row_key="id",
                        pagination={"rowsPerPage": 10},
                    ).classes("w-full ws-card")

        # Implementation logic for loading and rendering GIS data
        async def render_inspector(item: dict, item_type: str):
            inspector_container.clear()
            inspector_badge.text = item_type.upper()

            with inspector_container:
                if item_type == "observation":
                    inspector_badge.classes("ws-pill-cyan", remove="ws-pill-amber ws-pill-rose ws-pill-emerald")
                    temp = format_temperature(item.get("temperature"))
                    cond = item.get("weather_condition") or "Unknown"

                    with ui.row().classes("w-full items-center justify-between pb-2 border-b border-slate-700"):
                        with ui.column().classes("gap-0"):
                            ui.label(temp).classes("text-3xl font-extrabold text-white")
                            ui.label(cond).classes("text-xs text-cyan-300 font-medium")
                        ui.label(item.get("source", "OBSERVATION")).classes("ws-pill ws-pill-cyan")

                    with ui.grid(columns=2).classes("w-full gap-2 text-xs py-1"):
                        with ui.card().classes("p-2 rounded border border-slate-800 bg-slate-900/50"):
                            ui.label("Humidity").classes("ws-dim text-[11px]")
                            ui.label(format_metric(item.get("humidity"), "%")).classes("font-semibold text-white")

                        with ui.card().classes("p-2 rounded border border-slate-800 bg-slate-900/50"):
                            ui.label("Pressure").classes("ws-dim text-[11px]")
                            ui.label(format_metric(item.get("pressure"), "hPa")).classes("font-semibold text-white")

                        with ui.card().classes("p-2 rounded border border-slate-800 bg-slate-900/50"):
                            ui.label("Rainfall").classes("ws-dim text-[11px]")
                            ui.label(format_metric(item.get("rainfall"), "mm")).classes("font-semibold text-white")

                        with ui.card().classes("p-2 rounded border border-slate-800 bg-slate-900/50"):
                            ui.label("Wind Speed").classes("ws-dim text-[11px]")
                            ui.label(format_metric(item.get("wind_speed"), "m/s")).classes("font-semibold text-white")

                    with ui.column().classes("w-full gap-1 pt-1 text-[11px] ws-muted"):
                        coords = extract_observation_coordinates(item)
                        coord_str = f"{coords[0]:.4f}° N, {coords[1]:.4f}° E" if coords else "Not in response payload"
                        ui.label(f"GPS Coordinates: {coord_str}").classes("font-mono text-cyan-400" if coords else "text-slate-500")
                        ui.label(f"Observed: {format_timestamp(item.get('observed_at'))}")
                        ui.label(f"Location ID: {item.get('location_id')}")

                        if coords:
                            ui.button(
                                "Center Map on Marker",
                                icon="gps_fixed",
                                on_click=lambda c=coords: map_instance.run_map_method("flyTo", [c[0], c[1]], 14),
                            ).props("flat dense").classes("ws-button ws-btn-secondary text-xs mt-2 w-full")

                elif item_type == "event":
                    resolution = item.get("_resolution") or get_event_location_resolution(item, known_coords_by_location)
                    sev = (item.get("severity") or "").lower()
                    if sev in {"extreme", "high"}:
                        inspector_badge.classes("ws-pill-rose", remove="ws-pill-cyan ws-pill-amber ws-pill-emerald")
                    else:
                        inspector_badge.classes("ws-pill-amber", remove="ws-pill-cyan ws-pill-rose ws-pill-emerald")

                    conf = float(item.get("confidence_score") or 0.0)

                    with ui.row().classes("w-full items-center justify-between pb-2 border-b border-slate-700"):
                        with ui.column().classes("gap-0"):
                            ui.label(item.get("event_type", "Event").upper()).classes("text-2xl font-extrabold text-white")
                            ui.label(f"Confidence: {conf*100:.0f}%").classes("text-xs text-amber-300 font-medium")
                        ui.label(sev.upper()).classes(get_severity_badge_class(sev))

                    with ui.column().classes("w-full gap-2 text-xs py-2"):
                        # Geospatial resolution status
                        if resolution["is_mappable"]:
                            ev_c = resolution["coordinates"]
                            with ui.card().classes("p-2.5 rounded border border-emerald-800 bg-emerald-950/30 w-full"):
                                with ui.row().classes("items-center justify-between"):
                                    ui.label("Map Status").classes("text-emerald-400 font-semibold text-[11px]")
                                    ui.label("Plotted (GPS)").classes("ws-pill ws-pill-emerald text-[10px]")
                                ui.label(f"GPS Coordinates: {ev_c[0]:.4f}° N, {ev_c[1]:.4f}° E").classes("font-mono text-xs text-white mt-1")
                                ui.label(resolution["reason"]).classes("text-[11px] ws-muted")

                            ui.button(
                                "Center Map on Event Marker",
                                icon="gps_fixed",
                                on_click=lambda c=ev_c: map_instance.run_map_method("flyTo", [c[0], c[1]], 14),
                            ).props("unelevated dense").classes("ws-button ws-btn-primary text-xs w-full")
                        else:
                            with ui.card().classes("p-2.5 rounded border border-amber-800/80 bg-amber-950/20 w-full"):
                                with ui.row().classes("items-center justify-between"):
                                    ui.label("Map Status").classes("text-amber-400 font-semibold text-[11px]")
                                    ui.label("Marker Omitted").classes("ws-pill ws-pill-amber text-[10px]")
                                ui.label(resolution["reason"]).classes("text-xs text-slate-200 mt-1 leading-relaxed")
                                ui.label("Geospatial integrity: Marker omitted to prevent fabricated positions.").classes("text-[10px] text-amber-300/80 mt-1")

                        with ui.card().classes("p-2.5 rounded border border-slate-800 bg-slate-900/50 w-full"):
                            ui.label("Detection Source").classes("ws-dim text-[11px]")
                            ui.label(item.get("source", "Detection Pipeline")).classes("font-semibold text-white")

                        with ui.card().classes("p-2.5 rounded border border-slate-800 bg-slate-900/50 w-full"):
                            ui.label("Event Start Time").classes("ws-dim text-[11px]")
                            ui.label(format_timestamp(item.get("start_time"))).classes("font-semibold text-white")

                        if item.get("end_time"):
                            with ui.card().classes("p-2.5 rounded border border-slate-800 bg-slate-900/50 w-full"):
                                ui.label("Event End Time").classes("ws-dim text-[11px]")
                                ui.label(format_timestamp(item.get("end_time"))).classes("font-semibold text-white")

                        ui.label(f"Target Location ID: {item.get('location_id')}").classes("text-[11px] ws-muted font-mono mt-1")

        async def load_gis_data():
            refresh_btn.disable()
            status_kpi_label.text = "Loading..."
            status_kpi_label.classes("text-amber-400", remove="text-emerald-400 text-rose-400")

            # Remove previous marker layers
            for lyr in active_observation_layers + active_event_layers:
                try:
                    map_instance.remove_layer(lyr)
                except Exception:
                    pass
            active_observation_layers.clear()
            active_event_layers.clear()

            try:
                # 1. Fetch Observations
                src = source_filter.value if source_filter.value != "All" else None
                obs_res = await get_weather_observations(source=src, page=1, page_size=100)
                obs_items = obs_res.get("items", [])
                total_obs = obs_res.get("total", len(obs_items))
                total_obs_label.text = str(total_obs)

                # Track verified coordinates by location_id
                known_coords_by_location = {}
                geocoded_count = 0
                first_coord = None

                table_rows = []
                for obs in obs_items:
                    coords = extract_observation_coordinates(obs)
                    loc_id = str(obs.get("location_id", "")).strip()

                    if coords:
                        geocoded_count += 1
                        if loc_id and loc_id not in known_coords_by_location:
                            known_coords_by_location[loc_id] = coords
                        if first_coord is None:
                            first_coord = coords

                        # Create observation marker if layer toggle is ON
                        if show_obs_toggle.value:
                            lat, lon = coords
                            marker = map_instance.marker(latlng=(lat, lon))
                            active_observation_layers.append(marker)

                            # Bind popup
                            temp_str = format_temperature(obs.get("temperature"))
                            cond_str = html.escape(str(obs.get("weather_condition") or "Weather Observation"))
                            src_str = html.escape(str(obs.get("source") or "Live Station"))
                            time_str = format_timestamp(obs.get("observed_at"))

                            popup_html = f"""
                            <div style="font-family: inherit; font-size: 12px; min-width: 170px;">
                                <div style="font-weight: 700; color: #38bdf8; font-size: 14px; margin-bottom: 2px;">{temp_str}</div>
                                <div style="color: #94a3b8; font-size: 11px; margin-bottom: 6px;">{cond_str}</div>
                                <div style="border-top: 1px solid #223247; padding-top: 5px; font-size: 11px;">
                                    <div><strong>Source:</strong> {src_str}</div>
                                    <div><strong>Time:</strong> {time_str}</div>
                                </div>
                            </div>
                            """
                            map_instance.run_layer_method(marker.id, "bindPopup", popup_html)

                    # Build table row
                    table_rows.append({
                        "id": str(obs.get("id")),
                        "observed_at": format_timestamp(obs.get("observed_at")),
                        "source": obs.get("source", "Unknown"),
                        "temperature": format_temperature(obs.get("temperature")),
                        "humidity": format_metric(obs.get("humidity"), "%"),
                        "pressure": format_metric(obs.get("pressure"), "hPa"),
                        "rainfall": format_metric(obs.get("rainfall"), "mm"),
                        "wind": format_metric(obs.get("wind_speed"), "m/s"),
                        "coordinates": "Plotted (GPS)" if coords else "No GPS in payload",
                        "condition": obs.get("weather_condition") or "—",
                        "_raw": obs,
                    })

                geocoded_label.text = str(geocoded_count)
                obs_table.rows = table_rows
                obs_table.update()

                # 2. Fetch Weather Events
                etype = event_type_filter.value if event_type_filter.value != "All" else None
                esev = severity_filter.value if severity_filter.value != "All" else None
                events_res = await get_weather_events(event_type=etype, severity=esev, page=1, page_size=50)
                event_items = events_res.get("items", [])
                total_events_label.text = str(events_res.get("total", len(event_items)))

                # Plot event markers ONLY if coordinates are strictly verified
                mappable_events_count = 0
                unmapped_events_count = 0
                event_table_rows = []

                for ev in event_items:
                    resolution = get_event_location_resolution(ev, known_coords_by_location)
                    ev["_resolution"] = resolution

                    if resolution["is_mappable"]:
                        mappable_events_count += 1
                        ev_coords = resolution["coordinates"]

                        if show_events_toggle.value:
                            sev = (ev.get("severity") or "").lower()
                            color = "#ef4444" if sev in {"extreme", "high"} else "#f59e0b"

                            circle = map_instance.generic_layer(
                                name="circleMarker",
                                args=[
                                    [ev_coords[0], ev_coords[1]],
                                    {
                                        "radius": 14,
                                        "color": color,
                                        "fillColor": color,
                                        "fillOpacity": 0.75,
                                        "weight": 2,
                                    },
                                ],
                            )
                            active_event_layers.append(circle)

                            ev_type_str = html.escape(str(ev.get("event_type") or "Severe Weather").upper())
                            sev_str = html.escape(sev.upper())
                            conf_str = f"{float(ev.get('confidence_score') or 0)*100:.0f}%"

                            popup_html = f"""
                            <div style="font-family: inherit; font-size: 12px; min-width: 170px;">
                                <div style="font-weight: 700; color: {color}; font-size: 13px; margin-bottom: 2px;">{ev_type_str} ({sev_str})</div>
                                <div style="color: #cbd5e1; font-size: 11px; margin-bottom: 5px;">Confidence Score: <strong>{conf_str}</strong></div>
                                <div style="border-top: 1px solid #223247; padding-top: 4px; font-size: 11px; color: #94a3b8;">
                                    <div><strong>Source:</strong> {html.escape(str(ev.get('source', 'Pipeline')))}</div>
                                    <div><strong>Start:</strong> {format_timestamp(ev.get('start_time'))}</div>
                                    <div style="margin-top: 4px; color: #34d399;">✓ {html.escape(resolution['reason'])}</div>
                                </div>
                            </div>
                            """
                            map_instance.run_layer_method(circle.id, "bindPopup", popup_html)
                    else:
                        unmapped_events_count += 1
                        # Map marker is completely omitted to avoid fabricated positions

                    event_table_rows.append({
                        "id": str(ev.get("id")),
                        "event_type": str(ev.get("event_type", "Unknown")).upper(),
                        "severity": str(ev.get("severity", "Unknown")).upper(),
                        "confidence": f"{float(ev.get('confidence_score') or 0)*100:.0f}%",
                        "start_time": format_timestamp(ev.get("start_time")),
                        "source": ev.get("source", "Detection Pipeline"),
                        "location_id": str(ev.get("location_id")),
                        "map_status": (
                            f"Mapped ({resolution['coordinates'][0]:.2f}°, {resolution['coordinates'][1]:.2f}°)"
                            if resolution["is_mappable"]
                            else "Marker Omitted (No GPS)"
                        ),
                        "reason": resolution["reason"],
                        "_raw": ev,
                    })

                events_table.rows = event_table_rows
                events_table.update()
                events_map_status_label.text = f"{mappable_events_count} Plotted · {unmapped_events_count} Omitted"

                # Set first item to inspector if available
                if obs_items:
                    await render_inspector(obs_items[0], "observation")
                elif event_items:
                    await render_inspector(event_items[0], "event")

                # If geocoded records found, center view
                if first_coord:
                    map_instance.set_center(first_coord)

                status_kpi_label.text = "Operational"
                status_kpi_label.classes("text-emerald-400", remove="text-amber-400 text-rose-400")
                table_status_label.text = (
                    f"Loaded {len(obs_items)} observations ({geocoded_count} geocoded) and "
                    f"{len(event_items)} events ({mappable_events_count} mapped, {unmapped_events_count} omitted)."
                )

            except Exception as exc:
                print(f"GIS Data loading error: {exc}")
                status_kpi_label.text = "Connection Error"
                status_kpi_label.classes("text-rose-400", remove="text-emerald-400 text-amber-400")
                ui.notify(f"Could not load GIS data from backend: {exc}", type="negative")
            finally:
                refresh_btn.enable()

        async def on_obs_table_click(e):
            row = e.args.get("row")
            if row and row.get("_raw"):
                await render_inspector(row["_raw"], "observation")
                coords = extract_observation_coordinates(row["_raw"])
                if coords:
                    map_instance.run_map_method("flyTo", [coords[0], coords[1]], 14)

        async def on_events_table_click(e):
            row = e.args.get("row")
            if row and row.get("_raw"):
                await render_inspector(row["_raw"], "event")
                res = row["_raw"].get("_resolution") or get_event_location_resolution(row["_raw"], known_coords_by_location)
                if res["is_mappable"]:
                    coords = res["coordinates"]
                    map_instance.run_map_method("flyTo", [coords[0], coords[1]], 14)

        obs_table.on("rowClick", on_obs_table_click)
        events_table.on("rowClick", on_events_table_click)

        refresh_btn.on_click(load_gis_data)
        apply_filter_btn.on_click(load_gis_data)
        reset_view_btn.on_click(lambda: map_instance.run_map_method("flyTo", list(DEFAULT_CENTER), DEFAULT_ZOOM))

        async def reset_filters():
            source_filter.value = "All"
            event_type_filter.value = "All"
            severity_filter.value = "All"
            await load_gis_data()

        reset_filter_btn.on_click(reset_filters)

        # Trigger data load on page initialization
        ui.timer(0.3, load_gis_data, once=True)


# ---------------------------------------------------------
# Page 3: Priority 2 — Weather Event Monitoring Dashboard
# ---------------------------------------------------------

@ui.page("/events")
async def events_monitoring_page():
    """Render Weather Event Monitoring and Severity Analytics dashboard."""
    configure_page("WeatherSentinel | Weather Event Monitoring")

    with ui.column().classes("ws-page w-full px-4 sm:px-6 py-4"):
        render_navigation_header("/events")

        with ui.row().classes("w-full max-w-7xl mx-auto items-center justify-between gap-4 flex-wrap mb-4"):
            with ui.column().classes("gap-0"):
                ui.label("Weather Event Monitoring").classes("text-2xl font-extrabold text-white")
                ui.label("Severe weather detection, severity grading, and multi-hazard feed").classes("text-sm ws-muted")

            refresh_events_btn = ui.button(
                "Refresh Events",
                icon="refresh",
            ).props("unelevated").classes("ws-button ws-btn-primary")

        # Severity Metrics
        with ui.row().classes("w-full max-w-7xl mx-auto gap-4 flex-wrap mb-6"):
            with ui.card().classes("ws-card flex-grow p-4").style("min-width: 170px"):
                ui.label("Extreme Severity").classes("text-xs ws-muted uppercase tracking-wider")
                extreme_count_label = ui.label("0").classes("text-2xl font-bold text-rose-400")

            with ui.card().classes("ws-card flex-grow p-4").style("min-width: 170px"):
                ui.label("High Severity").classes("text-xs ws-muted uppercase tracking-wider")
                high_count_label = ui.label("0").classes("text-2xl font-bold text-amber-400")

            with ui.card().classes("ws-card flex-grow p-4").style("min-width: 170px"):
                ui.label("Medium Severity").classes("text-xs ws-muted uppercase tracking-wider")
                med_count_label = ui.label("0").classes("text-2xl font-bold text-cyan-400")

            with ui.card().classes("ws-card flex-grow p-4").style("min-width: 170px"):
                ui.label("Total Events").classes("text-xs ws-muted uppercase tracking-wider")
                total_events_count_label = ui.label("—").classes("text-2xl font-bold text-white")

        # Filter bar
        with ui.card().classes("w-full max-w-7xl mx-auto ws-card p-4 mb-6"):
            with ui.row().classes("w-full items-center justify-between gap-3 flex-wrap"):
                with ui.row().classes("items-center gap-3 flex-wrap"):
                    event_type_select = ui.select(
                        options=["All", "rainfall", "heatwave", "thunderstorm", "flooding", "fog", "other"],
                        value="All",
                        label="Hazard Type",
                    ).props("outlined dense").classes("w-44 text-xs")

                    severity_select = ui.select(
                        options=["All", "extreme", "high", "medium", "low"],
                        value="All",
                        label="Severity Level",
                    ).props("outlined dense").classes("w-44 text-xs")

                    apply_btn = ui.button(
                        "Filter",
                        icon="filter_alt",
                    ).props("unelevated").classes("ws-button ws-btn-primary text-xs px-4 py-2")

        # Events Table
        with ui.card().classes("w-full max-w-7xl mx-auto ws-card p-4 mb-10"):
            events_table = ui.table(
                columns=[
                    {"name": "event_type", "label": "Hazard Event", "field": "event_type", "align": "left", "sortable": True},
                    {"name": "severity", "label": "Severity", "field": "severity", "align": "center"},
                    {"name": "confidence", "label": "Confidence", "field": "confidence", "align": "right"},
                    {"name": "start_time", "label": "Detection Time", "field": "start_time", "align": "left"},
                    {"name": "map_status", "label": "Geospatial Status", "field": "map_status", "align": "center"},
                    {"name": "source", "label": "Source", "field": "source", "align": "left"},
                    {"name": "resolution_reason", "label": "Resolution & Omission Rationale", "field": "resolution_reason", "align": "left"},
                ],
                rows=[],
                row_key="id",
                pagination={"rowsPerPage": 15},
            ).classes("w-full")

        async def load_events():
            refresh_events_btn.disable()
            try:
                etype = event_type_select.value if event_type_select.value != "All" else None
                esev = severity_select.value if severity_select.value != "All" else None

                res = await get_weather_events(event_type=etype, severity=esev, page=1, page_size=100)
                items = res.get("items", [])
                total = res.get("total", len(items))

                total_events_count_label.text = str(total)

                # Count by severity
                extreme_count = sum(1 for e in items if (e.get("severity") or "").lower() == "extreme")
                high_count = sum(1 for e in items if (e.get("severity") or "").lower() == "high")
                med_count = sum(1 for e in items if (e.get("severity") or "").lower() == "medium")

                extreme_count_label.text = str(extreme_count)
                high_count_label.text = str(high_count)
                med_count_label.text = str(med_count)

                # Fetch observation telemetry to build verified location coordinate mapping
                obs_res = await get_weather_observations(page=1, page_size=100)
                known_coords = {}
                for o in obs_res.get("items", []):
                    c = extract_observation_coordinates(o)
                    lid = str(o.get("location_id", "")).strip()
                    if c and lid and lid not in known_coords:
                        known_coords[lid] = c

                events_table.rows = [
                    {
                        "id": str(e.get("id")),
                        "event_type": str(e.get("event_type", "Unknown")).upper(),
                        "severity": str(e.get("severity", "Unknown")).upper(),
                        "confidence": f"{float(e.get('confidence_score') or 0)*100:.0f}%",
                        "start_time": format_timestamp(e.get("start_time")),
                        "map_status": (
                            f"Mapped ({res['coordinates'][0]:.2f}°, {res['coordinates'][1]:.2f}°)"
                            if (res := get_event_location_resolution(e, known_coords))["is_mappable"]
                            else "Marker Omitted (No GPS)"
                        ),
                        "source": e.get("source", "Detection Pipeline"),
                        "resolution_reason": res["reason"],
                    }
                    for e in items
                ]
                events_table.update()

            except Exception as exc:
                print(f"Error loading events: {exc}")
                ui.notify(f"Could not load weather events: {exc}", type="negative")
            finally:
                refresh_events_btn.enable()

        refresh_events_btn.on_click(load_events)
        apply_btn.on_click(load_events)
        ui.timer(0.2, load_events, once=True)


# ---------------------------------------------------------
# Page 4: Priority 1 — Citizen Report Verification Hub
# ---------------------------------------------------------

@ui.page("/verification")
async def verification_page():
    """Render Citizen Report Verification & Telemetry Cross-Validation Hub."""
    configure_page("WeatherSentinel | Citizen Report Verification Hub")

    with ui.column().classes("ws-page w-full px-4 sm:px-6 py-4"):
        render_navigation_header("/verification")

        with ui.row().classes("w-full max-w-7xl mx-auto items-center justify-between gap-4 flex-wrap mb-4"):
            with ui.column().classes("gap-0"):
                ui.label("Citizen Weather Verification Hub").classes("text-2xl font-extrabold text-white")
                ui.label("Cross-validate crowdsourced weather reports against spatial sensor telemetry").classes("text-sm ws-muted")

            with ui.row().classes("items-center gap-3"):
                submit_report_btn = ui.button(
                    "Submit Weather Report",
                    icon="add_circle",
                ).props("unelevated").classes("ws-button bg-emerald-600 hover:bg-emerald-500 text-white font-semibold text-xs px-4 py-2")

                refresh_reports_btn = ui.button(
                    "Refresh Reports",
                    icon="refresh",
                ).props("unelevated").classes("ws-button ws-btn-primary")

        # KPI Metrics
        with ui.row().classes("w-full max-w-7xl mx-auto gap-4 flex-wrap mb-6"):
            with ui.card().classes("ws-card flex-grow p-4").style("min-width: 170px"):
                ui.label("Total Reports").classes("text-xs ws-muted uppercase tracking-wider")
                total_reports_label = ui.label("—").classes("text-2xl font-bold text-white")

            with ui.card().classes("ws-card flex-grow p-4").style("min-width: 170px"):
                ui.label("Verified Reports").classes("text-xs ws-muted uppercase tracking-wider")
                verified_count_label = ui.label("0").classes("text-2xl font-bold text-emerald-400")

            with ui.card().classes("ws-card flex-grow p-4").style("min-width: 170px"):
                ui.label("Suspicious Reports").classes("text-xs ws-muted uppercase tracking-wider")
                suspicious_count_label = ui.label("0").classes("text-2xl font-bold text-rose-400")

            with ui.card().classes("ws-card flex-grow p-4").style("min-width: 170px"):
                ui.label("Pending Verification").classes("text-xs ws-muted uppercase tracking-wider")
                pending_count_label = ui.label("0").classes("text-2xl font-bold text-amber-400")

        # Filter bar
        with ui.card().classes("w-full max-w-7xl mx-auto ws-card p-4 mb-6"):
            with ui.row().classes("w-full items-center justify-between gap-3 flex-wrap"):
                with ui.row().classes("items-center gap-3 flex-wrap"):
                    status_select = ui.select(
                        options=["All", "pending", "verified", "suspicious", "rejected"],
                        value="All",
                        label="Report Status",
                    ).props("outlined dense").classes("w-44 text-xs")

                    rep_event_type_select = ui.select(
                        options=["All", "rainfall", "heatwave", "thunderstorm", "flooding", "fog", "other"],
                        value="All",
                        label="Reported Event",
                    ).props("outlined dense").classes("w-44 text-xs")

                    apply_report_filter = ui.button(
                        "Apply Filter",
                        icon="filter_alt",
                    ).props("unelevated").classes("ws-button ws-btn-primary text-xs px-4 py-2")

        # Submission Feedback Banner Container
        submission_banner = ui.column().classes("w-full max-w-7xl mx-auto mb-4")

        # Verification Results Modal / Card Area
        result_dialog = ui.dialog()
        with result_dialog, ui.card().classes("ws-card p-6").style("min-width: 440px; max-width: 600px"):
            modal_title = ui.label("Verification Assessment").classes("text-xl font-bold text-white mb-2")
            modal_content = ui.column().classes("w-full gap-3")
            with ui.row().classes("w-full justify-end mt-4"):
                ui.button("Close", on_click=result_dialog.close).props("flat").classes("ws-button ws-btn-secondary")

        # Citizen Report Submission Dialog Modal
        submission_dialog = ui.dialog().props("persistent")
        with submission_dialog, ui.card().classes("ws-card p-6").style("min-width: 520px; max-width: 680px; width: 100%"):
            with ui.row().classes("w-full items-center justify-between pb-3 border-b border-slate-700 mb-3"):
                with ui.column().classes("gap-0"):
                    ui.label("Submit Citizen Weather Report").classes("text-xl font-bold text-white")
                    ui.label("Log ground weather observations for telemetry cross-validation (SIH 2026)").classes("text-xs ws-muted")
                close_dialog_btn = ui.button(icon="close", on_click=submission_dialog.close).props("flat round dense").classes("text-slate-400 hover:text-white")

            form_error_box = ui.column().classes("w-full mb-3")

            # Row 1: Location & Condition
            with ui.row().classes("w-full gap-3 flex-wrap"):
                sub_location_select = ui.select(
                    options={},
                    label="Weather Station / Location *",
                ).props("outlined dense options-dense").classes("flex-1 text-xs").style("min-width: 240px")

                sub_event_type_select = ui.select(
                    options={et: et.replace("_", " ").title() for et in ALLOWED_CITIZEN_EVENT_TYPES},
                    value="rainfall",
                    label="Weather Condition *",
                ).props("outlined dense options-dense").classes("w-48 text-xs")

            # Row 2: Observation Timestamp
            with ui.row().classes("w-full items-center gap-2 mt-2"):
                sub_timestamp_input = ui.input(
                    label="Observation Timestamp (UTC/Local) *",
                    value=datetime.now().strftime("%Y-%m-%dT%H:%M"),
                ).props("outlined dense").classes("flex-1 text-xs")

                def set_timestamp_now():
                    sub_timestamp_input.value = datetime.now().strftime("%Y-%m-%dT%H:%M")

                ui.button("Now", icon="schedule", on_click=set_timestamp_now).props("flat dense").classes("ws-button ws-btn-secondary text-xs px-2 py-1")

            # Row 3: Optional Measurements
            with ui.expansion("Physical Measurements (Optional)", icon="thermostat").classes("w-full border border-slate-800 rounded-lg p-2 mt-2 bg-slate-900/30"):
                ui.label("Enter real-time observed meteorological readings if available:").classes("text-xs ws-muted mb-2")
                with ui.grid(columns=2).classes("w-full gap-3 text-xs"):
                    sub_temp_input = ui.number(label="Temperature (°C)", placeholder="e.g. 28.5", format="%.1f").props("outlined dense clearable").classes("w-full text-xs")
                    sub_rain_input = ui.number(label="Rainfall (mm)", placeholder="e.g. 15.0", format="%.1f").props("outlined dense clearable").classes("w-full text-xs")
                    sub_humidity_input = ui.number(label="Relative Humidity (%)", placeholder="e.g. 85", format="%.0f").props("outlined dense clearable").classes("w-full text-xs")
                    sub_wind_input = ui.number(label="Wind Speed (km/h)", placeholder="e.g. 18.0", format="%.1f").props("outlined dense clearable").classes("w-full text-xs")

            # Row 4: Ground Observation Notes
            with ui.column().classes("w-full gap-1 mt-2"):
                ui.label("Observation Notes & Local Impacts * (min 5 characters)").classes("text-xs font-semibold text-slate-300")
                sub_notes_input = ui.textarea(
                    placeholder="e.g. Heavy sudden downpour observed with water accumulation on roads...",
                ).props("outlined dense rows=3").classes("w-full text-xs")

            # Row 5: Evidence Image URL
            sub_image_input = ui.input(
                label="Photo / Image Evidence URL (Optional)",
                placeholder="https://example.com/photo.jpg",
            ).props("outlined dense clearable").classes("w-full text-xs mt-1")

            # Footer Action Buttons
            with ui.row().classes("w-full items-center justify-between pt-4 border-t border-slate-700 mt-3"):
                ui.label("* Required fields").classes("text-[11px] ws-dim")
                with ui.row().classes("gap-2"):
                    cancel_btn = ui.button("Cancel", on_click=submission_dialog.close).props("flat").classes("ws-button ws-btn-secondary text-xs px-3")
                    submit_action_btn = ui.button(
                        "Submit Weather Report",
                        icon="cloud_upload",
                    ).props("unelevated").classes("ws-button bg-emerald-600 hover:bg-emerald-500 text-white font-semibold text-xs px-4 py-2")

        # Reports Table
        with ui.card().classes("w-full max-w-7xl mx-auto ws-card p-4 mb-10"):
            reports_container = ui.column().classes("w-full gap-4")

        is_submitting_report = False
        locations_cache = []

        async def load_location_options():
            nonlocal locations_cache
            try:
                locs = await get_locations()
                locations_cache = locs
                opts = {}
                for loc in locs:
                    lid = loc.get("id")
                    name = loc.get("name", "Unknown Station")
                    state = loc.get("state", "India")
                    district = loc.get("district", "")
                    label = f"{name} ({district}, {state})" if district else f"{name} ({state})"
                    opts[lid] = label
                sub_location_select.options = opts
                if opts and not sub_location_select.value:
                    sub_location_select.value = next(iter(opts))
                sub_location_select.update()
            except Exception as exc:
                print(f"Failed to load locations: {exc}")

        async def open_submission_dialog():
            form_error_box.clear()
            sub_notes_input.value = ""
            sub_temp_input.value = None
            sub_rain_input.value = None
            sub_humidity_input.value = None
            sub_wind_input.value = None
            sub_image_input.value = ""
            sub_timestamp_input.value = datetime.now().strftime("%Y-%m-%dT%H:%M")
            await load_location_options()
            submission_dialog.open()

        submit_report_btn.on_click(open_submission_dialog)

        async def handle_submit_report():
            nonlocal is_submitting_report
            if is_submitting_report:
                return

            form_error_box.clear()

            # Gather form inputs
            loc_id = sub_location_select.value
            event_type = sub_event_type_select.value
            timestamp_str = (sub_timestamp_input.value or "").strip()
            notes = (sub_notes_input.value or "").strip()
            image_url = (sub_image_input.value or "").strip() or None

            measurements = {}
            if sub_temp_input.value is not None:
                measurements["temperature"] = sub_temp_input.value
            if sub_rain_input.value is not None:
                measurements["rainfall"] = sub_rain_input.value
            if sub_humidity_input.value is not None:
                measurements["humidity"] = sub_humidity_input.value
            if sub_wind_input.value is not None:
                measurements["wind_speed"] = sub_wind_input.value

            # Format combined description
            formatted_desc = format_citizen_report_description(notes, measurements)

            # Validate
            validation_payload = {
                "location_id": loc_id,
                "event_type": event_type,
                "reported_at": timestamp_str,
                "description": formatted_desc,
                "measurements": measurements,
            }
            is_valid, error_msg = validate_citizen_report_submission(validation_payload)
            if not is_valid:
                with form_error_box:
                    with ui.card().classes("w-full p-2.5 rounded border border-rose-500/50 bg-rose-950/40"):
                        ui.label(f"Validation Error: {error_msg}").classes("text-xs text-rose-300 font-medium")
                ui.notify(error_msg, type="warning")
                return

            # Prepare API request payload
            # Format timestamp to ISO 8601 with timezone if possible
            try:
                parsed_dt = datetime.fromisoformat(timestamp_str)
                if parsed_dt.tzinfo is None:
                    iso_timestamp = parsed_dt.isoformat() + "Z"
                else:
                    iso_timestamp = parsed_dt.isoformat()
            except Exception:
                iso_timestamp = timestamp_str

            api_payload = {
                "location_id": str(loc_id),
                "event_type": str(event_type).lower(),
                "description": formatted_desc,
                "reported_at": iso_timestamp,
                "image_url": image_url,
            }

            # Set submitting lock & UI indicators
            is_submitting_report = True
            submit_action_btn.disable()
            submit_action_btn.props("loading=true")
            cancel_btn.disable()
            close_dialog_btn.disable()

            try:
                ui.notify("Submitting weather report to backend...", type="info")
                created_report = await create_citizen_report(api_payload)

                # Confirmed persistence from backend
                rep_id = created_report.get("id")
                rep_status = created_report.get("status", "pending")

                # Close dialog
                submission_dialog.close()

                # Refresh report list
                await load_reports()

                # Display high-visibility success banner with direct verification action
                submission_banner.clear()
                loc_label = sub_location_select.options.get(loc_id, str(loc_id))
                with submission_banner:
                    with ui.card().classes("w-full p-4 rounded-xl border border-emerald-500/50 bg-emerald-950/30 flex flex-col gap-2 shadow-lg mb-2"):
                        with ui.row().classes("w-full items-center justify-between flex-wrap gap-2"):
                            with ui.row().classes("items-center gap-2"):
                                ui.icon("check_circle", size="sm").classes("text-emerald-400")
                                ui.label("Report Persisted Successfully!").classes("text-base font-bold text-white")
                                ui.label(f"ID: {rep_id}").classes("text-xs font-mono text-emerald-300 bg-emerald-900/60 px-2 py-0.5 rounded")
                                ui.label(f"STATUS: {rep_status.upper()}").classes("text-xs font-bold text-amber-300 bg-amber-900/50 px-2 py-0.5 rounded")
                            ui.button(
                                "Verify This Report Now",
                                icon="verified",
                                on_click=lambda rid=str(rep_id): run_verification(rid),
                            ).props("unelevated").classes("ws-button ws-btn-primary text-xs px-3 py-1.5 font-semibold")

                        ui.label(
                            f"Location: {loc_label} · Event: {event_type.upper()} · Observations: {formatted_desc}"
                        ).classes("text-xs text-slate-300 leading-relaxed")

                ui.notify(
                    f"Report successfully recorded in PostgreSQL! (ID: {str(rep_id)[:8]}...)",
                    type="positive",
                    duration=5.0,
                )

            except Exception as exc:
                print(f"Error submitting citizen report: {exc}")
                err_detail = str(exc)
                if hasattr(exc, "response") and exc.response is not None:
                    try:
                        resp_json = exc.response.json()
                        if "detail" in resp_json:
                            err_detail = str(resp_json["detail"])
                    except Exception:
                        pass

                with form_error_box:
                    with ui.card().classes("w-full p-2.5 rounded border border-rose-500/50 bg-rose-950/40"):
                        ui.label(f"Submission Failed: {err_detail}").classes("text-xs text-rose-300 font-medium")

                ui.notify(f"Submission failed: {err_detail}", type="negative")

            finally:
                is_submitting_report = False
                submit_action_btn.enable()
                submit_action_btn.props("loading=false")
                cancel_btn.enable()
                close_dialog_btn.enable()

        submit_action_btn.on_click(handle_submit_report)

        async def run_verification(report_id: str):
            try:
                ui.notify("Running telemetry cross-verification...", type="info")
                result = await verify_citizen_report(report_id)

                modal_content.clear()
                with modal_content:
                    score = float(result.get("credibility_score", 0.0))
                    vstatus = result.get("verification_status", "uncertain")
                    reason = result.get("verification_reason", "No verification reason provided.")
                    model_ver = result.get("model_version", "rule-based-v1")
                    supp = result.get("supporting_observations") or {}

                    with ui.row().classes("items-center justify-between w-full pb-3 border-b border-slate-700"):
                        with ui.column().classes("gap-0"):
                            ui.label(f"Credibility Score: {score:.2f} / 1.00").classes("text-xl font-extrabold text-white")
                            ui.label(f"Model Engine: {model_ver}").classes("text-xs ws-dim")
                        ui.label(vstatus.replace("_", " ").upper()).classes(get_status_badge_class(vstatus))

                    # Credibility bar
                    ui.linear_progress(value=score, show_value=False).props("color=cyan").classes("w-full rounded")

                    with ui.card().classes("p-3 rounded border border-slate-800 bg-slate-900/60 w-full"):
                        ui.label("Verification Rationale").classes("text-xs font-semibold text-cyan-300 mb-1")
                        ui.label(reason).classes("text-xs leading-relaxed text-slate-200")

                    with ui.grid(columns=2).classes("w-full gap-2 text-xs"):
                        with ui.card().classes("p-2.5 rounded border border-slate-800 bg-slate-900/40"):
                            ui.label("Nearby Observations").classes("ws-dim text-[11px]")
                            ui.label(str(supp.get("observation_count", 0))).classes("text-base font-bold text-white")

                        with ui.card().classes("p-2.5 rounded border border-slate-800 bg-slate-900/40"):
                            ui.label("Matching Weather Events").classes("ws-dim text-[11px]")
                            ui.label(str(supp.get("event_count", 0))).classes("text-base font-bold text-white")

                result_dialog.open()
                ui.notify("Verification completed successfully!", type="positive")
                await load_reports()

            except Exception as exc:
                print(f"Verification error: {exc}")
                ui.notify(f"Verification failed: {exc}", type="negative")

        async def load_reports():
            refresh_reports_btn.disable()
            try:
                st = status_select.value if status_select.value != "All" else None
                etype = rep_event_type_select.value if rep_event_type_select.value != "All" else None

                res = await get_citizen_reports(status=st, event_type=etype, page=1, page_size=50)
                items = res.get("items", [])
                total = res.get("total", len(items))

                total_reports_label.text = str(total)
                verified_count_label.text = str(sum(1 for r in items if (r.get("status") or "").lower() == "verified"))
                suspicious_count_label.text = str(sum(1 for r in items if (r.get("status") or "").lower() == "suspicious"))
                pending_count_label.text = str(sum(1 for r in items if (r.get("status") or "").lower() == "pending"))

                reports_container.clear()
                with reports_container:
                    if not items:
                        with ui.column().classes("w-full items-center justify-center p-8 text-center"):
                            ui.icon("inventory_2", size="lg").style("color: #64748b")
                            ui.label("No citizen reports matching filter criteria.").classes("text-sm ws-muted mt-2")
                    else:
                        for r in items:
                            rid = str(r.get("id"))
                            rstatus = (r.get("status") or "pending").lower()
                            revent = str(r.get("event_type", "weather")).upper()

                            with ui.card().classes("w-full p-4 rounded-xl border border-slate-800 bg-slate-900/40 flex flex-col gap-2"):
                                with ui.row().classes("w-full items-center justify-between flex-wrap gap-2"):
                                    with ui.row().classes("items-center gap-2"):
                                        ui.label(revent).classes("text-base font-bold text-white")
                                        ui.label(rstatus.upper()).classes(get_status_badge_class(rstatus))
                                    ui.label(format_timestamp(r.get("reported_at"))).classes("text-xs ws-muted")

                                ui.label(r.get("description", "No description provided.")).classes("text-sm text-slate-300 leading-relaxed py-1")

                                with ui.row().classes("w-full items-center justify-between pt-2 border-t border-slate-800 text-xs flex-wrap gap-2"):
                                    ui.label(f"Location ID: {r.get('location_id')}").classes("text-[11px] ws-dim font-mono")
                                    ui.button(
                                        "Run Verification" if rstatus == "pending" else "Re-verify",
                                        icon="verified",
                                        on_click=lambda report_id=rid: run_verification(report_id),
                                    ).props("unelevated dense").classes(
                                        "ws-button ws-btn-primary text-xs px-3 py-1.5" if rstatus == "pending" else "ws-button ws-btn-secondary text-xs px-3 py-1.5"
                                    )

            except Exception as exc:
                print(f"Error loading citizen reports: {exc}")
                ui.notify(f"Could not load citizen reports: {exc}", type="negative")
            finally:
                refresh_reports_btn.enable()

        refresh_reports_btn.on_click(load_reports)
        apply_report_filter.on_click(load_reports)
        ui.timer(0.2, load_reports, once=True)


# ---------------------------------------------------------
# Page 5: Forecast Dashboard (Preserved & Enhanced)
# ---------------------------------------------------------

def create_forecast_chart(records):
    """Create Plotly chart from temperature forecast records."""
    figure = go.Figure()
    valid_records = []

    for record in records:
        timestamp = record.get("created_at")
        temperature = record.get("predicted_temperature_c")

        if timestamp is None or temperature is None:
            continue

        try:
            parsed_timestamp = datetime.fromisoformat(
                str(timestamp).replace("Z", "+00:00")
            )
            numeric_temperature = float(temperature)
        except (TypeError, ValueError):
            continue

        valid_records.append({
            "timestamp": parsed_timestamp,
            "temperature": numeric_temperature,
            "location": record.get("location", "Unknown"),
            "model": record.get("model_name", "Unknown"),
        })

    valid_records.sort(key=lambda item: item["timestamp"])

    if valid_records:
        figure.add_trace(go.Scatter(
            x=[item["timestamp"] for item in valid_records],
            y=[item["temperature"] for item in valid_records],
            mode="lines+markers",
            name="Predicted temperature",
            line={"color": "#38bdf8", "width": 2},
            marker={"size": 7, "color": "#67e8f9"},
            text=[
                f"Location: {item['location']}<br>"
                f"Model: {item['model']}"
                for item in valid_records
            ],
            hovertemplate=(
                "%{x|%d %b %Y, %H:%M UTC}<br>"
                "Predicted temperature: %{y:.2f} °C<br>"
                "%{text}<extra></extra>"
            ),
        ))

    figure.update_layout(
        template="plotly_dark",
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font={"color": "#cbd5e1"},
        xaxis_title="Forecast creation time",
        yaxis_title="Predicted temperature (°C)",
        hovermode="closest",
        margin={"l": 45, "r": 20, "t": 20, "b": 55},
        showlegend=False,
    )
    figure.update_xaxes(
        showgrid=True,
        gridcolor="rgba(148,163,184,0.12)",
        zeroline=False,
    )
    figure.update_yaxes(
        showgrid=True,
        gridcolor="rgba(148,163,184,0.12)",
        zeroline=False,
    )
    return figure


@ui.page("/dashboard")
async def dashboard_page():
    """Render forecast summaries, trend chart, and saved forecast records."""
    configure_page("WeatherSentinel | Forecast Analytics")

    current_page = 1
    page_size = 20
    total_records = 0

    with ui.column().classes("ws-page w-full px-4 sm:px-6 py-4"):
        render_navigation_header("/dashboard")

        with ui.row().classes("w-full max-w-7xl mx-auto items-center justify-between gap-4 flex-wrap mb-4"):
            with ui.column().classes("gap-0"):
                ui.label("Forecast Analytics").classes("text-2xl font-extrabold text-white")
                ui.label("Random Forest ML model inferences and temperature projection trends").classes("text-sm ws-muted")

            refresh_button = ui.button(
                "Refresh Forecasts",
                icon="refresh",
            ).props("unelevated").classes("ws-button ws-btn-primary")

        # Overview KPI Cards
        with ui.row().classes("w-full max-w-7xl mx-auto gap-4 flex-wrap mb-6"):
            with ui.card().classes("ws-card flex-grow p-4").style("min-width: 170px"):
                ui.label("Total Forecasts").classes("text-xs ws-muted uppercase tracking-wider")
                total_label = ui.label("—").classes("text-2xl font-bold text-white")

            with ui.card().classes("ws-card flex-grow p-4").style("min-width: 170px"):
                ui.label("Average Temperature").classes("text-xs ws-muted uppercase tracking-wider")
                average_label = ui.label("—").classes("text-2xl font-bold text-cyan-400")

            with ui.card().classes("ws-card flex-grow p-4").style("min-width: 170px"):
                ui.label("Minimum Temperature").classes("text-xs ws-muted uppercase tracking-wider")
                minimum_label = ui.label("—").classes("text-2xl font-bold text-blue-400")

            with ui.card().classes("ws-card flex-grow p-4").style("min-width: 170px"):
                ui.label("Maximum Temperature").classes("text-xs ws-muted uppercase tracking-wider")
                maximum_label = ui.label("—").classes("text-2xl font-bold text-amber-400")

        # Trend Chart Section
        with ui.card().classes("w-full max-w-7xl mx-auto ws-card p-5 mb-6"):
            with ui.row().classes("w-full items-center justify-between gap-4 flex-wrap mb-3"):
                with ui.column().classes("gap-0"):
                    ui.label("Temperature Trend Projection").classes("text-base font-bold text-white")
                    ui.label("Historical inferences sequenced by forecast generation timestamp.").classes("text-xs ws-muted")

                with ui.row().classes("items-center gap-2"):
                    location_filter = ui.input(
                        label="Filter by location",
                        placeholder="e.g. Pune",
                    ).props("outlined dense clearable").classes("w-52")

                    apply_button = ui.button(
                        "Apply",
                        icon="filter_alt",
                    ).props("unelevated").classes("ws-button ws-btn-primary text-xs px-3 py-2")

            chart = ui.plotly(create_forecast_chart([])).classes("w-full")

        # Forecast Records Table
        with ui.card().classes("w-full max-w-7xl mx-auto ws-card p-5 mb-10"):
            with ui.row().classes("w-full items-center justify-between gap-3 flex-wrap mb-3"):
                ui.label("Persisted Forecast Records").classes("text-base font-bold text-white")
                status = ui.label("Connecting to backend...").classes("text-xs ws-muted")

            forecast_table = ui.table(
                columns=[
                    {"name": "created_at", "label": "Created At (UTC)", "field": "created_at", "align": "left"},
                    {"name": "location", "label": "Location", "field": "location", "align": "left"},
                    {"name": "model", "label": "Model Engine", "field": "model", "align": "left"},
                    {"name": "horizon", "label": "Horizon (hours)", "field": "horizon", "align": "right"},
                    {"name": "temperature", "label": "Predicted Temperature", "field": "temperature", "align": "right"},
                ],
                rows=[],
                row_key="id",
            ).classes("w-full")

            with ui.row().classes("w-full items-center justify-between pt-4"):
                previous_button = ui.button(
                    "Previous",
                    icon="chevron_left",
                ).props("flat").classes("ws-button ws-btn-secondary")

                page_label = ui.label("Page 1").classes("text-xs ws-muted font-medium")

                next_button = ui.button(
                    "Next",
                    icon="chevron_right",
                ).props("flat").classes("ws-button ws-btn-secondary")

        async def load_summary():
            try:
                data = await get_forecast_summary()
                total_label.text = str(data.get("total_forecasts", 0))
                average_label.text = format_temperature(data.get("average_predicted_temperature_c"))
                minimum_label.text = format_temperature(data.get("minimum_predicted_temperature_c"))
                maximum_label.text = format_temperature(data.get("maximum_predicted_temperature_c"))
            except Exception as exc:
                print(f"Forecast summary error: {exc}")
                ui.notify("Could not load forecast summary.", type="warning")

        async def load_records():
            nonlocal total_records
            status.text = "Loading forecast records..."

            try:
                response = await get_forecasts(
                    location=(location_filter.value or "").strip() or None,
                    page=current_page,
                    page_size=page_size,
                )

                if isinstance(response, dict):
                    records = response.get("items", [])
                    total_records = int(response.get("total", len(records)))
                elif isinstance(response, list):
                    records = response
                    total_records = len(records)
                else:
                    raise ValueError("Unexpected forecast API response format")

                forecast_table.rows = [
                    {
                        "id": str(record.get("id", index)),
                        "created_at": format_timestamp(record.get("created_at")),
                        "location": record.get("location", "Unknown"),
                        "model": record.get("model_name", "Unknown"),
                        "horizon": record.get("forecast_horizon_hours", "—"),
                        "temperature": format_temperature(record.get("predicted_temperature_c")),
                    }
                    for index, record in enumerate(records)
                ]
                forecast_table.update()

                chart.figure = create_forecast_chart(records)
                chart.update()

                last_page = max(1, (total_records + page_size - 1) // page_size)
                page_label.text = f"Page {current_page} of {last_page}"

                if current_page > 1:
                    previous_button.enable()
                else:
                    previous_button.disable()

                if current_page < last_page:
                    next_button.enable()
                else:
                    next_button.disable()

                status.text = f"Showing {len(records)} of {total_records} matching forecasts."

            except Exception as exc:
                print(f"Forecast records error: {exc}")
                status.text = "Forecast records could not be loaded."
                ui.notify("Unable to load forecast records.", type="warning")

        async def refresh_dashboard():
            refresh_button.disable()
            try:
                await load_summary()
                await load_records()
            finally:
                refresh_button.enable()

        async def apply_filter():
            nonlocal current_page
            current_page = 1
            await load_records()

        async def previous_page():
            nonlocal current_page
            if current_page > 1:
                current_page -= 1
                await load_records()

        async def next_page():
            nonlocal current_page
            last_page = max(1, (total_records + page_size - 1) // page_size)
            if current_page < last_page:
                current_page += 1
                await load_records()

        refresh_button.on_click(refresh_dashboard)
        apply_button.on_click(apply_filter)
        previous_button.on_click(previous_page)
        next_button.on_click(next_page)

        previous_button.disable()
        next_button.disable()

        ui.timer(0.2, refresh_dashboard, once=True)


# ---------------------------------------------------------
# Application Entry Point
# ---------------------------------------------------------

if __name__ in {"__main__", "__mp_main__"}:
    ui.run(
        title="WeatherSentinel",
        host="127.0.0.1",
        port=8081,
        reload=False,
    )
