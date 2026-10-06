from __future__ import annotations

import argparse
from pathlib import Path

import joblib
import pandas as pd
from sklearn.metrics import classification_report, roc_auc_score
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import OneHotEncoder
from sklearn.compose import ColumnTransformer
from sklearn.pipeline import Pipeline
from lightgbm import LGBMClassifier

FEATURES = [
    "Type",
    "Air temperature [K]",
    "Process temperature [K]",
    "Rotational speed [rpm]",
    "Torque [Nm]",
    "Tool wear [min]",
]

def main() -> None:
    parser = argparse.ArgumentParser(description="Train a non-production challenger for Smart Factory.")
    parser.add_argument("--csv", required=True)
    parser.add_argument("--output", default="models/industrial/challenger_lgbm.joblib")
    args = parser.parse_args()

    df = pd.read_csv(args.csv)
    missing = [x for x in FEATURES + ["failure"] if x not in df.columns]
    if missing:
        raise SystemExit(f"Missing required columns: {missing}")
    X, y = df[FEATURES], df["failure"].astype(int)
    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, random_state=42, stratify=y
    )
    categorical = ["Type"]
    numeric = [x for x in FEATURES if x not in categorical]
    pre = ColumnTransformer([
        ("cat", OneHotEncoder(handle_unknown="ignore"), categorical),
        ("num", "passthrough", numeric),
    ])
    model = Pipeline([
        ("preprocess", pre),
        ("classifier", LGBMClassifier(n_estimators=250, random_state=42, verbosity=-1)),
    ])
    model.fit(X_train, y_train)
    proba = model.predict_proba(X_test)[:, 1]
    print(classification_report(y_test, (proba >= 0.5).astype(int)))
    print("ROC-AUC:", round(float(roc_auc_score(y_test, proba)), 4))
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    joblib.dump(model, output)
    print(f"Saved challenger model: {output}")

if __name__ == "__main__":
    main()
