from pathlib import Path
import json
import joblib
import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestRegressor
from sklearn.metrics import mean_absolute_error, mean_squared_error

BASE = Path(__file__).resolve().parents[2]
DATA_DIR = BASE / 'data' / 'industrial' / 'rul'
MODEL_DIR = BASE / 'models' / 'industrial'
MODEL_DIR.mkdir(parents=True, exist_ok=True)
FEATURE_NAMES = ['op_setting_1', 'op_setting_2', 'op_setting_3'] + [f'sensor_{i}' for i in range(1, 22)]
COLUMNS = ['unit', 'cycle'] + FEATURE_NAMES

def load_train():
    df = pd.read_csv(DATA_DIR / 'train_FD001.txt', sep=r'\s+', header=None)
    df = df.iloc[:, :26]
    df.columns = COLUMNS
    return df

def main():
    df = load_train()
    max_cycle = df.groupby('unit')['cycle'].transform('max')
    df['RUL'] = max_cycle - df['cycle']
    X = df[FEATURE_NAMES]
    y = df['RUL'].astype(float)
    split = int(len(X) * 0.8)
    X_train, X_val = X.iloc[:split], X.iloc[split:]
    y_train, y_val = y.iloc[:split], y.iloc[split:]
    model = RandomForestRegressor(n_estimators=250, random_state=42, n_jobs=-1, min_samples_leaf=2)
    model.fit(X_train, y_train)
    pred = np.maximum(model.predict(X_val), 0)
    mae = mean_absolute_error(y_val, pred)
    rmse = float(np.sqrt(mean_squared_error(y_val, pred)))
    model_path = MODEL_DIR / 'rul_model.joblib'
    joblib.dump(model, model_path)
    metrics = {'dataset':'NASA C-MAPSS FD001','rows':int(len(df)),'features':FEATURE_NAMES,'validation_rows':int(len(X_val)),'mae':float(mae),'rmse':rmse,'model':'RandomForestRegressor','model_version':'rf-rul-v1'}
    (MODEL_DIR / 'rul_metrics.json').write_text(json.dumps(metrics, indent=2), encoding='utf-8')
    schema = {'dataset':'NASA C-MAPSS FD001','features':FEATURE_NAMES,'target':'RUL','model_version':'rf-rul-v1'}
    (MODEL_DIR / 'rul_schema.json').write_text(json.dumps(schema, indent=2), encoding='utf-8')
    print('ROWS:', len(df))
    print('MAE:', round(float(mae), 4))
    print('RMSE:', round(rmse, 4))
    print('MODEL:', model_path)
    print('RUL TRAINING COMPLETE')

if __name__ == '__main__':
    main()
