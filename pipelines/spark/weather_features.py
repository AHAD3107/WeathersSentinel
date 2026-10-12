from pathlib import Path

from pyspark.sql import SparkSession
from pyspark.sql.functions import (
    avg,
    col,
    dayofweek,
    hour,
    lit,
    month,
    when,
    year,
)


# ============================================================
# PROJECT PATHS
# ============================================================

PROJECT_ROOT = Path(__file__).resolve().parents[2]

OBSERVATIONS_INPUT = (
    PROJECT_ROOT
    / "data"
    / "processed"
    / "noaa"
    / "observations"
)

FEATURES_OUTPUT = (
    PROJECT_ROOT
    / "data"
    / "processed"
    / "noaa"
    / "features"
)


# ============================================================
# SPARK SESSION
# ============================================================

spark = (
    SparkSession.builder
    .appName("WeatherSentinel-Weather-Feature-Engineering")
    .master("local[*]")
    .config(
        "spark.driver.host",
        "127.0.0.1",
    )
    .config(
        "spark.driver.bindAddress",
        "127.0.0.1",
    )
    .getOrCreate()
)

spark.sparkContext.setLogLevel("WARN")


# ============================================================
# START
# ============================================================

print("=" * 70)
print("WeatherSentinel - Weather Feature Engineering")
print("=" * 70)

print("\nReading processed observations:")
print(OBSERVATIONS_INPUT)


# ============================================================
# READ PROCESSED OBSERVATIONS
# ============================================================

df = spark.read.parquet(
    str(OBSERVATIONS_INPUT)
)

total_records = df.count()

print(
    f"\nInput records: {total_records}"
)


# ============================================================
# TEMPORAL FEATURES
# ============================================================

print("\nCreating temporal features...")

df = (
    df
    .withColumn(
        "hour",
        hour(col("observed_at")),
    )
    .withColumn(
        "day_of_week",
        dayofweek(col("observed_at")),
    )
    .withColumn(
        "month",
        month(col("observed_at")),
    )
    .withColumn(
        "year",
        year(col("observed_at")),
    )
)


# ============================================================
# SEASON FEATURE
# ============================================================

df = df.withColumn(
    "season",
    when(
        col("month").isin(12, 1, 2),
        lit("winter"),
    )
    .when(
        col("month").isin(3, 4, 5),
        lit("summer"),
    )
    .when(
        col("month").isin(6, 7, 8, 9),
        lit("monsoon"),
    )
    .otherwise(
        lit("post_monsoon"),
    ),
)


# ============================================================
# DAILY STATISTICS
# ============================================================

print("Calculating daily weather statistics...")

daily_stats = (
    df
    .groupBy(
        "year",
        "month",
        "day",
    )
    .agg(
        avg(
            "temperature_c"
        ).alias(
            "daily_avg_temperature_c"
        ),
        avg(
            "pressure_hpa"
        ).alias(
            "daily_avg_pressure_hpa"
        ),
        avg(
            "wind_speed_ms"
        ).alias(
            "daily_avg_wind_speed_ms"
        ),
    )
)


# ============================================================
# DAILY MIN/MAX VALUES
# ============================================================

from pyspark.sql.functions import min as spark_min
from pyspark.sql.functions import max as spark_max


daily_extremes = (
    df
    .groupBy(
        "year",
        "month",
        "day",
    )
    .agg(
        spark_min(
            "temperature_c"
        ).alias(
            "daily_min_temperature_c"
        ),
        spark_max(
            "temperature_c"
        ).alias(
            "daily_max_temperature_c"
        ),
        spark_max(
            "wind_speed_ms"
        ).alias(
            "daily_max_wind_speed_ms"
        ),
    )
)


# ============================================================
# JOIN DAILY STATISTICS
# ============================================================

df = (
    df
    .join(
        daily_stats,
        on=[
            "year",
            "month",
            "day",
        ],
        how="left",
    )
    .join(
        daily_extremes,
        on=[
            "year",
            "month",
            "day",
        ],
        how="left",
    )
)


# ============================================================
# TEMPERATURE FEATURES
# ============================================================

print("Creating temperature features...")

df = (
    df
    .withColumn(
        "daily_temperature_range_c",
        col("daily_max_temperature_c")
        - col("daily_min_temperature_c"),
    )
    .withColumn(
        "temperature_deviation_from_daily_mean_c",
        col("temperature_c")
        - col("daily_avg_temperature_c"),
    )
)


# ============================================================
# PRESSURE FEATURES
# ============================================================

print("Creating pressure features...")

df = df.withColumn(
    "pressure_deviation_from_daily_mean_hpa",
    col("pressure_hpa")
    - col("daily_avg_pressure_hpa"),
)


# ============================================================
# WIND FEATURES
# ============================================================

print("Creating wind features...")

df = df.withColumn(
    "wind_speed_deviation_from_daily_mean_ms",
    col("wind_speed_ms")
    - col("daily_avg_wind_speed_ms"),
)


# ============================================================
# HEAT INTENSITY
# ============================================================

print("Creating heat intensity feature...")

df = df.withColumn(
    "heat_intensity",
    when(
        col("temperature_c") >= 40,
        lit(3),
    )
    .when(
        col("temperature_c") >= 35,
        lit(2),
    )
    .when(
        col("temperature_c") >= 30,
        lit(1),
    )
    .otherwise(
        lit(0),
    ),
)


# ============================================================
# STRONG WIND INDICATOR
# ============================================================

print("Creating strong wind indicator...")

df = df.withColumn(
    "strong_wind_indicator",
    when(
        col("wind_speed_ms") >= 15,
        lit(1),
    ).otherwise(
        lit(0)
    ),
)


# ============================================================
# SELECT ML FEATURES
# ============================================================

feature_df = df.select(
    "observed_at",

    # Base weather
    "temperature_c",
    "dew_point_c",
    "pressure_hpa",
    "wind_speed_ms",
    "wind_direction",

    # Precipitation
    "rainfall_1h_mm",
    "rainfall_6h_mm",

    # Temporal
    "hour",
    "day_of_week",
    "month",
    "year",
    "season",

    # Temperature
    "daily_min_temperature_c",
    "daily_max_temperature_c",
    "daily_temperature_range_c",
    "daily_avg_temperature_c",
    "temperature_deviation_from_daily_mean_c",

    # Pressure
    "daily_avg_pressure_hpa",
    "pressure_deviation_from_daily_mean_hpa",

    # Wind
    "daily_avg_wind_speed_ms",
    "daily_max_wind_speed_ms",
    "wind_speed_deviation_from_daily_mean_ms",

    # Event-related features
    "heat_intensity",
    "strong_wind_indicator",

    # Existing validation flag
    "record_valid",
)


# ============================================================
# CREATE OUTPUT DIRECTORY
# ============================================================

FEATURES_OUTPUT.mkdir(
    parents=True,
    exist_ok=True,
)


# ============================================================
# PERSIST FEATURES
# ============================================================

print("\n" + "=" * 70)
print("PERSISTING FEATURE DATASET")
print("=" * 70)

feature_df.write \
    .mode("overwrite") \
    .parquet(
        str(FEATURES_OUTPUT)
    )

print(
    "\nFeature dataset saved to:"
)

print(
    FEATURES_OUTPUT
)


# ============================================================
# VERIFY FEATURE DATASET
# ============================================================

saved_features_df = (
    spark.read.parquet(
        str(FEATURES_OUTPUT)
    )
)

saved_count = saved_features_df.count()

print(
    f"\nFeature records saved: {saved_count}"
)

print(
    f"Feature columns: {len(saved_features_df.columns)}"
)


# ============================================================
# DISPLAY SAMPLE
# ============================================================

print("\n" + "=" * 70)
print("FEATURE DATASET SAMPLE")
print("=" * 70)

saved_features_df.show(
    10,
    truncate=False,
)


# ============================================================
# FINAL VALIDATION
# ============================================================

if saved_count == total_records:
    print("\n" + "=" * 70)
    print("STATUS: SUCCESS")
    print("=" * 70)

    print(
        "Feature engineering completed successfully."
    )

    print(
        f"Input records:   {total_records}"
    )

    print(
        f"Feature records: {saved_count}"
    )

else:
    print("\n" + "=" * 70)
    print("STATUS: FAILURE")
    print("=" * 70)

    print(
        "Feature record count does not match "
        "the input record count."
    )


# ============================================================
# STOP SPARK
# ============================================================

spark.stop()