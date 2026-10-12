
from pathlib import Path

from pyspark.sql import SparkSession
from pyspark.sql import functions as F


PROJECT_ROOT = Path(__file__).resolve().parents[2]

INPUT_PATH = (
    PROJECT_ROOT / "data" / "processed" / "noaa" / "features"
)

OUTPUT_PATH = (
    PROJECT_ROOT / "data" / "processed" / "noaa" / "ml_dataset"
)

FORECAST_HORIZON_HOURS = 3
HEAT_THRESHOLD_C = 40.0
STRONG_WIND_THRESHOLD_MS = 15.0


def main():
    spark = (
        SparkSession.builder
        .appName("WeatherSentinel-ML-Dataset")
        .master("local[2]")
        .config("spark.driver.host", "127.0.0.1")
        .config("spark.driver.bindAddress", "127.0.0.1")
        .getOrCreate()
    )

    spark.sparkContext.setLogLevel("WARN")

    try:
        print("=" * 65)
        print("WEATHERSENTINEL - ML DATASET GENERATION")
        print("=" * 65)

        if not INPUT_PATH.exists():
            raise FileNotFoundError(
                f"Feature dataset not found: {INPUT_PATH}"
            )

        df = spark.read.parquet(str(INPUT_PATH))

        required_columns = {
            "observed_at",
            "temperature_c",
            "dew_point_c",
            "pressure_hpa",
            "wind_speed_ms",
            "wind_direction",
            "hour",
            "day_of_week",
            "month",
            "season",
        }

        missing_columns = required_columns - set(df.columns)

        if missing_columns:
            raise ValueError(
                f"Missing required columns: {sorted(missing_columns)}"
            )

        input_count = df.count()
        print(f"\nInput feature records: {input_count}")

        # Only current weather and calendar features are predictors.
        # Same-day aggregates and threshold-derived indicators are
        # deliberately excluded to prevent leakage.
        predictor_columns = [
            "temperature_c",
            "dew_point_c",
            "pressure_hpa",
            "wind_speed_ms",
            "wind_direction",
            "hour",
            "day_of_week",
            "month",
            "season",
        ]

        current = df.select(
            "observed_at",
            *predictor_columns,
        ).withColumn(
            "target_time",
            F.expr(
                f"observed_at + INTERVAL {FORECAST_HORIZON_HOURS} HOURS"
            ),
        )

        # Match the observation at the exact future timestamp.
        # Do not assume the next row is three hours later.
        future = df.select(
            F.col("observed_at").alias("target_time"),
            F.col("temperature_c").alias("future_temperature_c"),
            F.col("wind_speed_ms").alias("future_wind_speed_ms"),
        )

        joined = current.join(
            future,
            on="target_time",
            how="left",
        )

        matched_count = joined.filter(
            F.col("future_temperature_c").isNotNull()
            & F.col("future_wind_speed_ms").isNotNull()
        ).count()

        print(
            f"Records with valid exact +{FORECAST_HORIZON_HOURS}h "
            f"targets: {matched_count}"
        )

        # A missing future temperature or wind value means the
        # full target class cannot be reliably determined.
        labeled = joined.filter(
            F.col("future_temperature_c").isNotNull()
            & F.col("future_wind_speed_ms").isNotNull()
        )

        heat = (
            F.col("future_temperature_c") >= HEAT_THRESHOLD_C
        )

        strong_wind = (
            F.col("future_wind_speed_ms")
            >= STRONG_WIND_THRESHOLD_MS
        )

        labeled = labeled.withColumn(
            "event_label",
            F.when(
                heat & strong_wind,
                F.lit("COMBINED_EVENT"),
            )
            .when(
                heat,
                F.lit("HEAT_EVENT"),
            )
            .when(
                strong_wind,
                F.lit("STRONG_WIND_EVENT"),
            )
            .otherwise(
                F.lit("NORMAL"),
            ),
        )

        labeled = labeled.withColumn(
            "event_label_id",
            F.when(
                F.col("event_label") == "NORMAL", 0
            )
            .when(
                F.col("event_label") == "HEAT_EVENT", 1
            )
            .when(
                F.col("event_label") == "STRONG_WIND_EVENT", 2
            )
            .otherwise(3),
        )

        # Future measurements are used to create labels but are
        # deliberately excluded from the saved predictor dataset.
        output_columns = [
            "observed_at",
            "target_time",
            *predictor_columns,
            "event_label",
            "event_label_id",
        ]

        ml_dataset = labeled.select(*output_columns)

        output_count = ml_dataset.count()

        print(f"\nFinal labeled records: {output_count}")

        print("\nCLASS DISTRIBUTION")
        print("-" * 65)

        (
            ml_dataset.groupBy("event_label", "event_label_id")
            .count()
            .orderBy("event_label_id")
            .show(truncate=False)
        )

        print("MISSING CURRENT PREDICTOR VALUES")
        print("-" * 65)

        ml_dataset.select(
            *[
                F.sum(
                    F.col(column).isNull().cast("int")
                ).alias(f"{column}_nulls")
                for column in predictor_columns
            ]
        ).show(truncate=False)

        print("SAMPLE LABELED RECORDS")
        print("-" * 65)

        ml_dataset.orderBy("observed_at").show(
            10,
            truncate=False,
        )

        OUTPUT_PATH.parent.mkdir(
            parents=True,
            exist_ok=True,
        )

        ml_dataset.write.mode("overwrite").parquet(
            str(OUTPUT_PATH)
        )

        saved_count = spark.read.parquet(
            str(OUTPUT_PATH)
        ).count()

        print(f"\nSaved dataset: {OUTPUT_PATH}")
        print(f"Input records: {input_count}")
        print(f"Labeled records: {output_count}")
        print(f"Saved records: {saved_count}")

        if saved_count != output_count:
            raise RuntimeError(
                "Saved record count does not match output count."
            )

        print("\nSTATUS: SUCCESS")
        print(
            "Next step: evaluate class balance and "
            "prepare time-based model splits."
        )

    finally:
        spark.stop()


if __name__ == "__main__":
    main()
