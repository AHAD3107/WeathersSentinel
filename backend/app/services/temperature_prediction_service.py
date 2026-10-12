"""Reusable service for three-hour-ahead temperature predictions."""

from pathlib import Path
from typing import Any

import joblib
import numpy as np


# Project root: WeatherSentinel/
PROJECT_ROOT = Path(__file__).resolve().parents[3]
MODEL_PATH = PROJECT_ROOT / "ml" / "models" / "temperature_3h_model.joblib"


class TemperaturePredictionService:
    """Load the trained model and predict temperature three hours ahead."""

    def __init__(self, model_path: Path = MODEL_PATH) -> None:
        if not model_path.is_file():
            raise FileNotFoundError(
                f"Temperature model not found: {model_path}"
            )

        artifact = joblib.load(model_path)

        self.model = artifact["model"]
        self.model_name = artifact["model_name"]
        self.features = artifact["features"]
        self.forecast_horizon_hours = artifact["forecast_horizon_hours"]
        self.location = artifact["location"]

    def predict(self, observation: dict[str, Any]) -> dict[str, Any]:
        """Predict future temperature from one weather observation.

        Missing feature values are represented as NaN. The trained model
        pipeline handles missing values using its fitted imputer.
        """
        values = []

        for feature in self.features:
            value = observation.get(feature)

            if value is None:
                values.append(np.nan)
            else:
                try:
                    values.append(float(value))
                except (TypeError, ValueError) as exc:
                    raise ValueError(
                        f"Feature '{feature}' must be numeric or None."
                    ) from exc

        prediction = float(
            self.model.predict(np.asarray([values], dtype=float))[0]
        )

        return {
            "model": self.model_name,
            "location": self.location,
            "forecast_horizon_hours": self.forecast_horizon_hours,
            "predicted_temperature_c": round(prediction, 2),
        }


# Convenient reusable instance for application code.
temperature_prediction_service = TemperaturePredictionService()
