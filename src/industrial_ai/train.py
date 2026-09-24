import json
from pathlib import Path

import joblib
import pandas as pd

from sklearn.model_selection import train_test_split
from sklearn.compose import ColumnTransformer
from sklearn.preprocessing import OneHotEncoder, StandardScaler
from sklearn.pipeline import Pipeline
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import (
    classification_report,
    confusion_matrix,
    roc_auc_score,
    average_precision_score,
)


BASE = Path(__file__).resolve().parents[2]

DATA = BASE / "data" / "industrial" / "ai4i2020.csv"
OUT = BASE / "models" / "industrial"

OUT.mkdir(parents=True, exist_ok=True)


print("=" * 60)
print("INDUSTRIAL PREDICTIVE MAINTENANCE TRAINING")
print("=" * 60)

print(f"Dataset: {DATA}")

df = pd.read_csv(DATA)

print(f"Dataset shape: {df.shape}")


TARGET = "Machine failure"

# Remove identifiers and failure-mode columns.
# Failure-mode columns are excluded to avoid target leakage.
DROP = [
    "UDI",
    "Product ID",
    "TWF",
    "HDF",
    "PWF",
    "OSF",
    "RNF",
]


features = [
    column
    for column in df.columns
    if column not in DROP + [TARGET]
]


X = df[features].copy()
y = df[TARGET].astype(int)


categorical_features = ["Type"]

numerical_features = [
    column
    for column in features
    if column not in categorical_features
]


preprocess = ColumnTransformer(
    transformers=[
        (
            "num",
            StandardScaler(),
            numerical_features,
        ),
        (
            "cat",
            OneHotEncoder(handle_unknown="ignore"),
            categorical_features,
        ),
    ]
)


model = RandomForestClassifier(
    n_estimators=400,
    max_depth=14,
    min_samples_leaf=2,
    class_weight="balanced",
    random_state=42,
    n_jobs=-1,
)


pipeline = Pipeline(
    steps=[
        ("preprocess", preprocess),
        ("model", model),
    ]
)


X_train, X_test, y_train, y_test = train_test_split(
    X,
    y,
    test_size=0.20,
    stratify=y,
    random_state=42,
)


print()
print("Training model...")

pipeline.fit(X_train, y_train)


probabilities = pipeline.predict_proba(X_test)[:, 1]

predictions = (
    probabilities >= 0.50
).astype(int)


roc_auc = roc_auc_score(
    y_test,
    probabilities,
)

average_precision = average_precision_score(
    y_test,
    probabilities,
)

report = classification_report(
    y_test,
    predictions,
    output_dict=True,
)

matrix = confusion_matrix(
    y_test,
    predictions,
)


metrics = {
    "dataset": "UCI AI4I 2020 Predictive Maintenance Dataset",
    "rows": int(len(df)),
    "train_rows": int(len(X_train)),
    "test_rows": int(len(X_test)),
    "features": features,
    "roc_auc": float(roc_auc),
    "average_precision": float(average_precision),
    "classification_report": report,
    "confusion_matrix": matrix.tolist(),
}


model_path = OUT / "failure_model.joblib"
metrics_path = OUT / "metrics.json"
schema_path = OUT / "schema.json"


joblib.dump(
    pipeline,
    model_path,
)


metrics_path.write_text(
    json.dumps(metrics, indent=2),
    encoding="utf-8",
)


schema_path.write_text(
    json.dumps(
        {
            "target": TARGET,
            "features": features,
            "categorical_features": categorical_features,
            "numerical_features": numerical_features,
        },
        indent=2,
    ),
    encoding="utf-8",
)


print()
print("=" * 60)
print("TRAINING COMPLETE")
print("=" * 60)

print(f"Rows:               {len(df)}")
print(f"Training rows:      {len(X_train)}")
print(f"Testing rows:       {len(X_test)}")
print(f"Features:           {len(features)}")
print(f"ROC-AUC:            {roc_auc:.4f}")
print(f"Average Precision:  {average_precision:.4f}")

print()
print("MODEL:")
print(model_path)

print()
print("METRICS:")
print(metrics_path)

print()
print("SCHEMA:")
print(schema_path)

print("=" * 60)