"""Prepare a dataset for predicting temperature three hours ahead."""

from pathlib import Path

from pyspark.sql import SparkSession, functions as F

ROOT = Path(__file__).resolve().parents[2]
FEATURES_PATH = ROOT / "data/processed/noaa/features"
OUTPUT_PATH = ROOT / "data/processed/noaa/temperature_dataset"
HORIZON_HOURS = 3

FEATURES = [
    "temperature_c",
    "dew_point_c",
    "pressure_hpa",
    "wind_speed_ms",
    "wind_direction",
    "hour",
    "day_of_week",
    "month",
]


def main():
    if not FEATURES_PATH.exists():
        raise FileNotFoundError(
            f"Feature dataset not found: {FEATURES_PATH}"
        )

    spark = (
        SparkSession.builder
        .appName("WeatherSentinel-CreateTemperatureDataset")
        .master("local[*]")
        .getOrCreate()
    )
    spark.sparkContext.setLogLevel("WARN")

    try:
        source = spark.read.parquet(str(FEATURES_PATH))

        required = ["observed_at", *FEATURES]
        missing = sorted(set(required) - set(source.columns))
        if missing:
            raise ValueError(f"Missing source columns: {missing}")

        source = (
            source
            .withColumn("observed_at", F.to_timestamp("observed_at"))
            .filter(F.col("observed_at").isNotNull())
            .select("observed_at", *FEATURES)
        )

        future = source.select(
            F.col("observed_at").alias("target_time"),
            F.col("temperature_c").alias("target_temperature_c"),
        )

        dataset = (
            source
            .withColumn(
                "target_time",
                F.col("observed_at")
                + F.expr(f"INTERVAL {HORIZON_HOURS} HOURS"),
            )
            .join(future, on="target_time", how="inner")
            .filter(
                F.col("temperature_c").isNotNull()
                & F.col("target_temperature_c").isNotNull()
            )
            .select(
                "observed_at",
                "target_time",
                *FEATURES,
                "target_temperature_c",
            )
            .orderBy("observed_at")
        )

        count = dataset.count()
        print(f"Source observations: {source.count()}")
        print(f"Forecast horizon: {HORIZON_HOURS} hours")
        print(f"Prepared records: {count}")

        print("\nMissing predictor counts:")
        dataset.select(*[
            F.sum(
                F.when(F.col(name).isNull(), 1).otherwise(0)
            ).alias(name)
            for name in FEATURES
        ]).show(truncate=False)

        print("\nTarget temperature summary:")
        dataset.select(
            F.mean("target_temperature_c").alias("mean_c"),
            F.stddev("target_temperature_c").alias("stddev_c"),
            F.min("target_temperature_c").alias("min_c"),
            F.max("target_temperature_c").alias("max_c"),
        ).show(truncate=False)

        print("\nSample records:")
        dataset.show(5, truncate=False)

        OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
        dataset.write.mode("overwrite").parquet(str(OUTPUT_PATH))

        print(f"Dataset saved to: {OUTPUT_PATH}")

    finally:
        spark.stop()


if __name__ == "__main__":
    main()
