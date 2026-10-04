from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation
from pathlib import Path
from uuid import UUID, uuid4

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models.weather_observation import WeatherObservation
from app.services.event_detection_service import create_events_from_observation
from app.services.weather_validation_service import validate_observation


NOAA_SOURCE = "NOAA_ISD_LITE"


def _parse_decimal(
    value: str,
    scale: Decimal = Decimal("1"),
) -> Decimal | None:
    """
    Convert a NOAA numeric field into Decimal.

    NOAA uses -9999 for missing values.
    """
    value = value.strip()

    if not value or value == "-9999":
        return None

    try:
        return Decimal(value) / scale
    except (InvalidOperation, ValueError):
        return None


def _parse_precipitation(value: str) -> Decimal | None:
    """
    Parse NOAA ISD-Lite precipitation.

    NOAA:
        -9999 = missing
        -1    = trace precipitation
        otherwise = tenths of millimeters
    """
    value = value.strip()

    if not value or value == "-9999":
        return None

    if value == "-1":
        return Decimal("0")

    try:
        return Decimal(value) / Decimal("10")
    except (InvalidOperation, ValueError):
        return None


def parse_noaa_isd_lite_line(line: str) -> dict | None:
    """
    Parse one NOAA ISD-Lite observation line.

    Expected fields:

        YEAR
        MONTH
        DAY
        HOUR
        AIR_TEMP
        DEW_POINT
        SEA_LEVEL_PRESSURE
        WIND_DIRECTION
        WIND_SPEED
        CLOUD_COVER
        1HR_PRECIP
        6HR_PRECIP

    NOAA ISD-Lite scaling:

        temperature       -> tenths of °C
        dew point         -> tenths of °C
        pressure          -> tenths of hPa
        wind speed        -> tenths of m/s
        precipitation     -> tenths of mm
    """

    parts = line.split()

    if len(parts) < 12:
        return None

    try:
        year = int(parts[0])
        month = int(parts[1])
        day = int(parts[2])
        hour = int(parts[3])

        observed_at = datetime(
            year=year,
            month=month,
            day=day,
            hour=hour,
            tzinfo=timezone.utc,
        )

    except (ValueError, TypeError):
        return None

    temperature = _parse_decimal(
        parts[4],
        Decimal("10"),
    )

    dew_point = _parse_decimal(
        parts[5],
        Decimal("10"),
    )

    pressure = _parse_decimal(
        parts[6],
        Decimal("10"),
    )

    wind_direction = _parse_decimal(
        parts[7],
        Decimal("1"),
    )

    wind_speed = _parse_decimal(
        parts[8],
        Decimal("10"),
    )

    cloud_cover = _parse_decimal(
        parts[9],
        Decimal("1"),
    )

    precipitation_1h = _parse_precipitation(parts[10])

    precipitation_6h = _parse_precipitation(parts[11])

    return {
        "observed_at": observed_at,
        "temperature": temperature,
        "dew_point": dew_point,
        "pressure": pressure,
        "wind_direction": wind_direction,
        "wind_speed": wind_speed,
        "cloud_cover": cloud_cover,
        "rainfall": precipitation_1h,
        "precipitation_6h": precipitation_6h,
    }


def _observation_exists(
    db: Session,
    *,
    location_id: UUID,
    source: str,
    observed_at: datetime,
) -> bool:
    """
    Application-level duplicate check.

    The database UNIQUE constraint remains the final
    protection against race conditions.
    """

    return (
        db.query(WeatherObservation.id)
        .filter(
            WeatherObservation.location_id == location_id,
            WeatherObservation.source == source,
            WeatherObservation.observed_at == observed_at,
        )
        .first()
        is not None
    )


def ingest_noaa_isd_lite_file(
    db: Session,
    file_path: str | Path,
    location_id: UUID | str,
) -> dict:
    """
    Ingest a NOAA ISD-Lite file into WeatherSentinel.

    Features:

    - NOAA ISD-Lite parsing
    - data-quality validation
    - application-level duplicate detection
    - database-level duplicate protection
    - savepoint-based duplicate handling
    - automatic weather-event detection
    - transaction rollback on unexpected errors
    - ingestion statistics
    """

    file_path = Path(file_path)
    location_id = UUID(str(location_id))

    if not file_path.exists():
        raise FileNotFoundError(
            f"NOAA ISD-Lite file not found: {file_path}"
        )

    if not file_path.is_file():
        raise ValueError(
            f"Expected a file but received: {file_path}"
        )

    total_lines = 0
    successful_records = 0
    skipped_records = 0
    duplicate_records = 0
    validation_failures = 0
    detected_events = 0

    validation_errors: list[dict] = []

    try:

        with file_path.open(
            "r",
            encoding="utf-8",
            errors="replace",
        ) as file:

            for line_number, line in enumerate(file, start=1):

                total_lines += 1

                line = line.strip()

                # ---------------------------------------------------------
                # Empty line
                # ---------------------------------------------------------

                if not line:
                    skipped_records += 1
                    continue

                # ---------------------------------------------------------
                # Parse NOAA record
                # ---------------------------------------------------------

                parsed = parse_noaa_isd_lite_line(line)

                if parsed is None:
                    skipped_records += 1
                    continue

                observed_at = parsed["observed_at"]

                # ---------------------------------------------------------
                # Application-level duplicate check
                # ---------------------------------------------------------

                if _observation_exists(
                    db,
                    location_id=location_id,
                    source=NOAA_SOURCE,
                    observed_at=observed_at,
                ):
                    duplicate_records += 1
                    continue

                # ---------------------------------------------------------
                # Data validation
                # ---------------------------------------------------------

                is_valid, errors = validate_observation(
                    observed_at=observed_at,
                    temperature=parsed["temperature"],
                    pressure=parsed["pressure"],
                    rainfall=parsed["rainfall"],
                    wind_speed=parsed["wind_speed"],
                    wind_direction=parsed["wind_direction"],
                )

                if not is_valid:

                    validation_failures += 1

                    validation_errors.append(
                        {
                            "line_number": line_number,
                            "errors": errors,
                        }
                    )

                    continue

                # ---------------------------------------------------------
                # Preserve original NOAA values
                # ---------------------------------------------------------

                raw_data = {
                    "source_format": NOAA_SOURCE,
                    "line_number": line_number,

                    "temperature_c": (
                        str(parsed["temperature"])
                        if parsed["temperature"] is not None
                        else None
                    ),

                    "dew_point_c": (
                        str(parsed["dew_point"])
                        if parsed["dew_point"] is not None
                        else None
                    ),

                    "pressure_hpa": (
                        str(parsed["pressure"])
                        if parsed["pressure"] is not None
                        else None
                    ),

                    "wind_direction_deg": (
                        str(parsed["wind_direction"])
                        if parsed["wind_direction"] is not None
                        else None
                    ),

                    "wind_speed_mps": (
                        str(parsed["wind_speed"])
                        if parsed["wind_speed"] is not None
                        else None
                    ),

                    "cloud_cover": (
                        str(parsed["cloud_cover"])
                        if parsed["cloud_cover"] is not None
                        else None
                    ),

                    "precipitation_1h_mm": (
                        str(parsed["rainfall"])
                        if parsed["rainfall"] is not None
                        else None
                    ),

                    "precipitation_6h_mm": (
                        str(parsed["precipitation_6h"])
                        if parsed["precipitation_6h"] is not None
                        else None
                    ),
                }

                # ---------------------------------------------------------
                # Create observation
                # ---------------------------------------------------------

                observation = WeatherObservation(
                    id=uuid4(),
                    location_id=location_id,
                    source=NOAA_SOURCE,
                    observed_at=observed_at,
                    temperature=parsed["temperature"],
                    humidity=None,
                    pressure=parsed["pressure"],
                    rainfall=parsed["rainfall"],
                    wind_speed=parsed["wind_speed"],
                    wind_direction=parsed["wind_direction"],
                    visibility=None,
                    weather_condition=None,
                    raw_data=raw_data,
                )

                db.add(observation)

                # ---------------------------------------------------------
                # Database-level duplicate protection
                #
                # begin_nested() creates a SAVEPOINT.
                #
                # If PostgreSQL rejects this row because of the UNIQUE
                # constraint, only this row is rolled back.
                #
                # The rest of the ingestion transaction remains alive.
                # ---------------------------------------------------------

                try:

                    with db.begin_nested():
                        db.flush()

                except IntegrityError:

                    if _observation_exists(
                        db,
                        location_id=location_id,
                        source=NOAA_SOURCE,
                        observed_at=observed_at,
                    ):
                        duplicate_records += 1
                        continue

                    # Unexpected integrity error.
                    raise

                # ---------------------------------------------------------
                # Weather event detection
                # ---------------------------------------------------------

                events = create_events_from_observation(
                    db=db,
                    observation=observation,
                )

                detected_events += len(events)

                successful_records += 1

        # -------------------------------------------------------------
        # Commit the complete ingestion transaction
        # -------------------------------------------------------------

        db.commit()

    except Exception:
        db.rollback()
        raise

    return {
        "source": NOAA_SOURCE,
        "file": str(file_path),
        "location_id": str(location_id),
        "total_lines": total_lines,
        "successful_records": successful_records,
        "skipped_records": skipped_records,
        "duplicate_records": duplicate_records,
        "validation_failures": validation_failures,
        "detected_events": detected_events,
        "validation_errors": validation_errors,
    }