from pathlib import Path
import joblib
import pandas as pd

BASE = Path(__file__).resolve().parents[2]
MODEL_PATH = BASE / 'models' / 'industrial' / 'rul_model.joblib'

FEATURE_NAMES = ['op_setting_1', 'op_setting_2', 'op_setting_3'] + [f'sensor_{i}' for i in range(1, 22)]

_model = None

def load_model():
    global _model
    if _model is None:
        if not MODEL_PATH.exists():
            raise FileNotFoundError(f'RUL model not found: {MODEL_PATH}')
        _model = joblib.load(MODEL_PATH)
    return _model

def predict_rul(op_setting_1, op_setting_2, op_setting_3, sensors):
    if len(sensors) != 21:
        raise ValueError(f'Expected 21 sensor values, got {len(sensors)}')
    values = [op_setting_1, op_setting_2, op_setting_3] + list(sensors)
    data = pd.DataFrame([values], columns=FEATURE_NAMES)
    model = load_model()
    rul = max(0.0, float(model.predict(data)[0]))
    if rul <= 30:
        risk_level = 'HIGH'
    elif rul <= 75:
        risk_level = 'MEDIUM'
    else:
        risk_level = 'LOW'
    return {
        'predicted_rul_cycles': round(rul, 2),
        'risk_level': risk_level,
        'model': 'RandomForestRegressor',
        'model_version': 'rf-rul-v1'
    }
