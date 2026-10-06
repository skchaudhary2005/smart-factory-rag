from __future__ import annotations

import os
import re
from datetime import datetime, timezone
from statistics import mean, pstdev
from typing import Any

import psycopg
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from src.industrial_ai.rul_predict import predict_rul

router = APIRouter(prefix="/future", tags=["Future Intelligence"])
DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://factory:factory@postgres:5432/smartfactory")

LANGUAGE_NAMES = {"en": "English", "hi": "Hindi", "hinglish": "Hinglish"}

def detect_language(text: str) -> str:
    s = (text or "").lower()
    hindi_words = re.findall(r"[\u0900-\u097f]+", s)
    if hindi_words:
        return "hi"
    hinglish = {
        "kyu", "kyun", "kya", "kaise", "batao", "btao", "hai", "hain",
        "machine", "risk", "wala", "wali", "karna", "karo", "chahiye",
        "problem", "maintenance", "check", "bacha", "chal", "ho", "raha",
    }
    words = set(re.findall(r"[a-zA-Z]+", s))
    if len(words & hinglish) >= 2:
        return "hinglish"
    return "en"

def init_future_db() -> None:
    with psycopg.connect(DATABASE_URL) as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS maintenance_feedback (
                id BIGSERIAL PRIMARY KEY,
                machine_id TEXT NOT NULL,
                question TEXT,
                assessment_risk TEXT,
                feedback TEXT NOT NULL,
                created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
            )
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS maintenance_schedule (
                id BIGSERIAL PRIMARY KEY,
                machine_id TEXT NOT NULL,
                priority TEXT NOT NULL,
                action TEXT NOT NULL,
                scheduled_for TIMESTAMPTZ NOT NULL,
                status TEXT NOT NULL DEFAULT 'PLANNED',
                created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
            )
        """)
        conn.commit()

class FeedbackRequest(BaseModel):
    machine_id: str
    feedback: str = Field(..., min_length=1, max_length=2000)
    question: str = ""
    assessment_risk: str = "UNKNOWN"

class ScheduleRequest(BaseModel):
    machine_id: str
    priority: str = "MEDIUM"
    action: str = "Maintenance inspection"
    scheduled_for: datetime

class LanguageRequest(BaseModel):
    text: str = Field(..., min_length=1, max_length=2000)

class RULTelemetryRequest(BaseModel):
    op_setting_1: float
    op_setting_2: float
    op_setting_3: float
    sensors: list[float]

def _risk_level(probability: float) -> str:
    if probability >= 0.70:
        return "HIGH"
    if probability >= 0.30:
        return "MEDIUM"
    return "LOW"

@router.post("/language")
def language(request: LanguageRequest):
    code = detect_language(request.text)
    return {"language": code, "language_name": LANGUAGE_NAMES[code]}

@router.get("/anomalies/{machine_id}")
def anomalies(machine_id: str, limit: int = 100):
    limit = max(10, min(limit, 500))
    with psycopg.connect(DATABASE_URL) as conn:
        rows = conn.execute(
            """SELECT time, air_temperature, process_temperature, rotational_speed,
                      torque, tool_wear, failure_probability, risk_level
               FROM sensor_readings
               WHERE machine_id=%s AND machine_id <> 'derived'
               ORDER BY time DESC LIMIT %s""",
            (machine_id, limit),
        ).fetchall()
    rows = list(reversed(rows))
    if len(rows) < 10:
        return {"machine_id": machine_id, "anomalies": [], "baseline_ready": False, "sample_count": len(rows)}

    fields = [
        ("air_temperature", 1), ("process_temperature", 2), ("rotational_speed", 3),
        ("torque", 4), ("tool_wear", 5), ("failure_probability", 6),
    ]
    events: list[dict[str, Any]] = []
    baseline = rows[:-1]
    latest = rows[-1]
    for name, idx in fields:
        vals = [float(r[idx]) for r in baseline if r[idx] is not None]
        if len(vals) < 5:
            continue
        mu = mean(vals)
        sd = pstdev(vals)
        if sd <= 0:
            continue
        value = float(latest[idx])
        z = abs(value - mu) / sd
        if z >= 3:
            severity = "CRITICAL" if z >= 5 else "HIGH" if z >= 4 else "MEDIUM"
            events.append({
                "machine_id": machine_id, "sensor": name, "value": value,
                "baseline_mean": round(mu, 4), "baseline_std": round(sd, 4),
                "z_score": round(z, 2), "severity": severity,
                "time": latest[0],
            })
    return {"machine_id": machine_id, "anomalies": events, "baseline_ready": True, "sample_count": len(rows)}

@router.get("/alerts")
def alerts(limit: int = 50):
    limit = max(1, min(limit, 200))
    with psycopg.connect(DATABASE_URL) as conn:
        rows = conn.execute(
            """SELECT DISTINCT ON (machine_id)
                      machine_id, time, failure_probability, prediction, risk_level
               FROM sensor_readings
               WHERE machine_id <> 'derived'
               ORDER BY machine_id, time DESC"""
        ).fetchall()
    result = []
    for machine_id, ts, probability, prediction, risk in rows:
        p = float(probability or 0)
        if str(risk).upper() in {"HIGH", "MEDIUM"} or p >= 0.30:
            result.append({
                "machine_id": machine_id, "time": ts, "risk": risk,
                "failure_probability": p, "prediction": prediction,
                "priority": "CRITICAL" if p >= 0.70 else "HIGH" if p >= 0.30 else "MEDIUM",
                "recommended_action": "Inspect immediately" if p >= 0.70 else "Schedule inspection and monitor closely",
            })
    return {"alerts": result[:limit]}

@router.post("/feedback")
def feedback(request: FeedbackRequest):
    with psycopg.connect(DATABASE_URL) as conn:
        row = conn.execute(
            """INSERT INTO maintenance_feedback
               (machine_id, question, assessment_risk, feedback)
               VALUES (%s,%s,%s,%s) RETURNING id, created_at""",
            (request.machine_id, request.question, request.assessment_risk, request.feedback),
        ).fetchone()
        conn.commit()
    return {"saved": True, "feedback_id": row[0], "created_at": row[1]}

@router.post("/schedule")
def schedule(request: ScheduleRequest):
    priority = request.priority.upper()
    if priority not in {"LOW", "MEDIUM", "HIGH", "CRITICAL"}:
        raise HTTPException(400, "Invalid priority")
    with psycopg.connect(DATABASE_URL) as conn:
        row = conn.execute(
            """INSERT INTO maintenance_schedule
               (machine_id, priority, action, scheduled_for)
               VALUES (%s,%s,%s,%s) RETURNING id, status, created_at""",
            (request.machine_id, priority, request.action, request.scheduled_for),
        ).fetchone()
        conn.commit()
    return {"scheduled": True, "schedule_id": row[0], "status": row[1], "created_at": row[2]}

@router.get("/schedule/{machine_id}")
def schedules(machine_id: str, limit: int = 20):
    with psycopg.connect(DATABASE_URL) as conn:
        rows = conn.execute(
            """SELECT id, priority, action, scheduled_for, status, created_at
               FROM maintenance_schedule WHERE machine_id=%s
               ORDER BY scheduled_for DESC LIMIT %s""",
            (machine_id, max(1, min(limit, 100))),
        ).fetchall()
    return {"machine_id": machine_id, "schedules": [
        {"id": r[0], "priority": r[1], "action": r[2], "scheduled_for": r[3], "status": r[4], "created_at": r[5]}
        for r in rows
    ]}

@router.post("/rul/telemetry")
def rul_from_telemetry(request: RULTelemetryRequest):
    if len(request.sensors) != 21:
        raise HTTPException(400, f"Expected 21 sensor values, got {len(request.sensors)}")
    result = predict_rul(request.op_setting_1, request.op_setting_2, request.op_setting_3, request.sensors)
    return {"available": True, **result}

@router.get("/digital-twin")
def digital_twin():
    with psycopg.connect(DATABASE_URL) as conn:
        rows = conn.execute(
            """SELECT DISTINCT ON (machine_id)
                      machine_id, time, machine_type, air_temperature,
                      process_temperature, rotational_speed, torque, tool_wear,
                      failure_probability, prediction, risk_level
               FROM sensor_readings WHERE machine_id <> 'derived'
               ORDER BY machine_id, time DESC"""
        ).fetchall()
    return {"updated_at": datetime.now(timezone.utc), "machines": [
        {
            "machine_id": r[0], "time": r[1], "machine_type": r[2],
            "air_temperature": r[3], "process_temperature": r[4],
            "rotational_speed": r[5], "torque": r[6], "tool_wear": r[7],
            "failure_probability": r[8], "prediction": r[9], "risk_level": r[10],
        } for r in rows
    ]}

@router.get("/edge/status")
def edge_status():
    return {
        "mode": "cloud",
        "edge_ready": True,
        "inference_contract": "/industrial/predict",
        "telemetry_contract": "MQTT factory/#",
        "recommended_runtime": "ONNX/TFLite/TensorRT on industrial edge gateway",
        "note": "Cloud inference remains unchanged; this endpoint exposes an edge-compatible contract without changing the production path.",
    }
