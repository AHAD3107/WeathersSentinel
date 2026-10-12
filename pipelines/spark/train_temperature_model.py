"""Train and evaluate WeatherSentinel's 3-hour temperature models."""

import json
from pathlib import Path

import joblib
import numpy as np
from pyspark.sql import SparkSession, functions as F
from sklearn.ensemble import RandomForestRegressor
from sklearn.impute import SimpleImputer
from sklearn.linear_model import Ridge
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler

ROOT = Path(__file__).resolve().parents[2]
DATA_PATH = ROOT / "data/processed/noaa/temperature_dataset"
MODEL_PATH = ROOT / "ml/models/temperature_3h_model.joblib"
REPORT_PATH = ROOT / "ml/reports/temperature_3h_metrics.json"

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
TARGET = "target_temperature_c"


def calculate_metrics(actual, predicted):
    return {
        "mae_c": round(float(mean_absolute_error(actual, predicted)), 4),
        "rmse_c": round(
            float(np.sqrt(mean_squared_error(actual, predicted))), 4
        ),
        "r2": round(float(r2_score(actual, predicted)), 4),
    }


def main():
    if not DATA_PATH.exists():
        raise FileNotFoundError(f"Dataset not found: {DATA_PATH}")

    spark = (
        SparkSession.builder
        .appName("WeatherSentinel-Temperature-Training")
        .master("local[*]")
        .getOrCreate()
    )
    spark.sparkContext.setLogLevel("WARN")

    try:
        df = spark.read.parquet(str(DATA_PATH))

        required = ["target_time", *FEATURES, TARGET]
        missing = sorted(set(required) - set(df.columns))
        if missing:
            raise ValueError(f"Missing dataset columns: {missing}")

        df = (
            df.withColumn("target_time", F.to_timestamp("target_time"))
            .filter(
                F.col("target_time").isNotNull()
                & F.col("temperature_c").isNotNull()
                & F.col(TARGET).isNotNull()
            )
            .select("target_time", *FEATURES, TARGET)
            .orderBy("target_time")
        )

        # The dataset is small enough to collect for local scikit-learn.
        rows = df.collect()
    finally:
        spark.stop()

    if len(rows) < 100:
        raise ValueError(f"Too few usable records: {len(rows)}")

    timestamps = [row["target_time"].isoformat() for row in rows]

    # Convert Spark Rows to NumPy arrays. No pandas is used.
    X = np.asarray([
        [
            float(row[name]) if row[name] is not None else np.nan
            for name in FEATURES
        ]
        for row in rows
    ], dtype=np.float64)

    y = np.asarray(
        [float(row[TARGET]) for row in rows],
        dtype=np.float64,
    )
    persistence = X[:, FEATURES.index("temperature_c")]

    n = len(rows)
    train_end = int(n * 0.70)
    validation_end = int(n * 0.85)

    X_train, y_train = X[:train_end], y[:train_end]
    X_val, y_val = X[train_end:validation_end], y[train_end:validation_end]
    X_test, y_test = X[validation_end:], y[validation_end:]

    baseline_val = persistence[train_end:validation_end]
    baseline_test = persistence[validation_end:]

    models = {
        "ridge_regression": Pipeline([
            ("imputer", SimpleImputer(strategy="median")),
            ("scaler", StandardScaler()),
            ("model", Ridge(alpha=1.0)),
        ]),
        "random_forest": Pipeline([
            ("imputer", SimpleImputer(strategy="median")),
            ("model", RandomForestRegressor(
                n_estimators=300,
                min_samples_leaf=3,
                random_state=42,
                n_jobs=-1,
            )),
        ]),
    }

    print("\n=== WEATHER SENTINEL: TEMPERATURE TRAINING ===")
    print(f"Usable records: {n}")
    print(f"Training records: {len(X_train)}")
    print(f"Validation records: {len(X_val)}")
    print(f"Test records: {len(X_test)}")
    print(f"Training target period: {timestamps[0]} to "
          f"{timestamps[train_end - 1]}")
    print(f"Validation target period: {timestamps[train_end]} to "
          f"{timestamps[validation_end - 1]}")
    print(f"Test target period: {timestamps[validation_end]} to "
          f"{timestamps[-1]}")

    validation_results = {
        "persistence_baseline": calculate_metrics(y_val, baseline_val)
    }

    for name, model in models.items():
        model.fit(X_train, y_train)
        validation_results[name] = calculate_metrics(
            y_val, model.predict(X_val)
        )

    print("\n--- VALIDATION RESULTS ---")
    for name, result in validation_results.items():
        print(
            f"{name:24s} MAE={result['mae_c']:.4f} C | "
            f"RMSE={result['rmse_c']:.4f} C | R2={result['r2']:.4f}"
        )

    selected_name = min(
        models,
        key=lambda name: validation_results[name]["mae_c"],
    )
    selected_model = models[selected_name]

    # Refit on train + validation. The final test remains unseen.
    selected_model.fit(X[:validation_end], y[:validation_end])
    predictions = selected_model.predict(X_test)

    test_results = {
        "persistence_baseline": calculate_metrics(y_test, baseline_test),
        selected_name: calculate_metrics(y_test, predictions),
    }

    baseline_mae = test_results["persistence_baseline"]["mae_c"]
    model_mae = test_results[selected_name]["mae_c"]
    improvement = (
        (baseline_mae - model_mae) / baseline_mae * 100
        if baseline_mae > 0 else None
    )

    print("\n--- FINAL TEST RESULTS ---")
    for name, result in test_results.items():
        print(
            f"{name:24s} MAE={result['mae_c']:.4f} C | "
            f"RMSE={result['rmse_c']:.4f} C | R2={result['r2']:.4f}"
        )

    print(f"\nSelected model: {selected_name}")
    if improvement is not None:
        print(f"MAE improvement over baseline: {improvement:.2f}%")
    print(f"Beats baseline on test: {model_mae < baseline_mae}")

    MODEL_PATH.parent.mkdir(parents=True, exist_ok=True)
    REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)

    joblib.dump({
        "model": selected_model,
        "model_name": selected_name,
        "features": FEATURES,
        "target": TARGET,
        "forecast_horizon_hours": 3,
        "location": "Pune, India",
        "training_data_year": 2024,
    }, MODEL_PATH)

    report = {
        "task": "3-hour-ahead temperature regression",
        "location": "Pune, India",
        "data_year": 2024,
        "records_used": n,
        "features": FEATURES,
        "target": TARGET,
        "split": {
            "strategy": "chronological 70/15/15",
            "train_records": len(X_train),
            "validation_records": len(X_val),
            "test_records": len(X_test),
            "train_start": timestamps[0],
            "train_end": timestamps[train_end - 1],
            "validation_start": timestamps[train_end],
            "validation_end": timestamps[validation_end - 1],
            "test_start": timestamps[validation_end],
            "test_end": timestamps[-1],
        },
        "validation_metrics": validation_results,
        "test_metrics": test_results,
        "selected_model": selected_name,
        "test_mae_improvement_percent": (
            round(float(improvement), 2) if improvement is not None else None
        ),
        "beats_baseline_on_test": bool(model_mae < baseline_mae),
        "limitations": [
            "Historical data from one Pune station in 2024 only.",
            "Does not establish national forecast accuracy.",
            "Historical evaluation does not prove real-time accuracy.",
        ],
    }

    REPORT_PATH.write_text(json.dumps(report, indent=2), encoding="utf-8")

    print(f"\nModel saved: {MODEL_PATH.relative_to(ROOT)}")
    print(f"Metrics saved: {REPORT_PATH.relative_to(ROOT)}")
    print("Training and evaluation completed.")


if __name__ == "__main__":
    main()
