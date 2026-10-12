
from pathlib import Path

from pyspark.sql import SparkSession
from pyspark.sql import functions as F


PROJECT_ROOT = Path(__file__).resolve().parents[2]
DATASET_PATH = (
    PROJECT_ROOT / "data" / "processed" / "noaa" / "ml_dataset"
)


def main():
    spark = (
        SparkSession.builder
        .appName("WeatherSentinel-ML-Diagnostics")
        .master("local[2]")
        .config("spark.driver.host", "127.0.0.1")
        .config("spark.driver.bindAddress", "127.0.0.1")
        .getOrCreate()
    )

    spark.sparkContext.setLogLevel("WARN")

    try:
        df = spark.read.parquet(str(DATASET_PATH))

        print("\n=== OVERALL CLASS DISTRIBUTION ===")
        total = df.count()

        (
            df.groupBy("event_label")
            .agg(F.count("*").alias("records"))
            .withColumn(
                "percentage",
                F.round(F.col("records") * 100.0 / total, 3),
            )
            .orderBy(F.desc("records"))
            .show(truncate=False)
        )

        print("\n=== CLASS DISTRIBUTION BY MONTH ===")
        (
            df.withColumn("month", F.month("observed_at"))
            .groupBy("month", "event_label")
            .count()
            .orderBy("month", "event_label")
            .show(100, truncate=False)
        )

        print("\n=== POSITIVE EVENT TIMESTAMPS ===")
        (
            df.filter(F.col("event_label") != "NORMAL")
            .select(
                "observed_at",
                "target_time",
                "temperature_c",
                "wind_speed_ms",
                "event_label",
            )
            .orderBy("observed_at")
            .show(100, truncate=False)
        )

        print("\n=== MISSING PREDICTOR COUNTS ===")
        predictor_columns = [
            "temperature_c",
            "dew_point_c",
            "pressure_hpa",
            "wind_speed_ms",
            "wind_direction",
        ]

        df.select(
            *[
                F.sum(
                    F.col(c).isNull().cast("int")
                ).alias(c)
                for c in predictor_columns
            ]
        ).show(truncate=False)

        print("\n=== TIME-BASED YEAR SPLIT COUNTS ===")
        (
            df.withColumn(
                "period",
                F.when(
                    F.col("observed_at") < F.to_timestamp(
                        F.lit("2024-09-01 00:00:00")
                    ),
                    "TRAIN_JAN_AUG",
                ).otherwise("HOLDOUT_SEP_DEC"),
            )
            .groupBy("period", "event_label")
            .count()
            .orderBy("period", "event_label")
            .show(100, truncate=False)
        )

        print("\n=== DATASET DIAGNOSTICS COMPLETE ===")

    finally:
        spark.stop()


if __name__ == "__main__":
    main()
