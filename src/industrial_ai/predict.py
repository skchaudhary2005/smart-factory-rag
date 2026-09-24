from pathlib import Path
from typing import Any

import joblib
import pandas as pd


BASE = Path(__file__).resolve().parents[2]
MODEL_PATH = BASE / "models" / "industrial" / "failure_model.joblib"

_model = None


def load_model():
    global _model

    if _model is None:
        if not MODEL_PATH.exists():
            raise FileNotFoundError(
                f"Industrial model not found: {MODEL_PATH}"
            )

        _model = joblib.load(MODEL_PATH)

    return _model


def predict_failure(
    machine_type: str,
    air_temperature: float,
    process_temperature: float,
    rotational_speed: float,
    torque: float,
    tool_wear: float,
) -> dict[str, Any]:

    model = load_model()

    data = pd.DataFrame(
        [
            {
                "Type": machine_type,
                "Air temperature [K]": air_temperature,
                "Process temperature [K]": process_temperature,
                "Rotational speed [rpm]": rotational_speed,
                "Torque [Nm]": torque,
                "Tool wear [min]": tool_wear,
            }
        ]
    )

    probability = float(
        model.predict_proba(data)[0][1]
    )

    prediction = int(probability >= 0.50)

    if probability >= 0.70:
        risk_level = "HIGH"
    elif probability >= 0.30:
        risk_level = "MEDIUM"
    else:
        risk_level = "LOW"

    return {
        "prediction": (
            "FAILURE_RISK"
            if prediction
            else "NO_FAILURE"
        ),
        "failure_probability": round(
            probability,
            6,
        ),
        "failure_probability_percent": round(
            probability * 100,
            2,
        ),
        "risk_level": risk_level,
        "model": "RandomForest",
        "model_version": "rf-industrial-v1",
    }