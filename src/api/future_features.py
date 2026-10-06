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
from src.industrial_ai.predict import predict_failure

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
        "wala", "wali", "karna", "karo", "chahiye", "bacha", "chal",
        "ho", "raha", "rha", "rhi", "krna", "kr", "bta", "batao",
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

@router.get("/rul/live/{machine_id}")
def live_rul(machine_id: str):
    with psycopg.connect(DATABASE_URL) as conn:
        row = conn.execute(
            """SELECT time, telemetry_payload FROM sensor_readings
               WHERE machine_id=%s AND telemetry_payload IS NOT NULL
               ORDER BY time DESC LIMIT 1""",
            (machine_id,),
        ).fetchone()
    if not row:
        return {"available": False, "reason": "No raw telemetry payload is available for this machine."}
    payload = row[1] or {}
    sensors = payload.get("sensors") or payload.get("cmaps_sensors")
    if not isinstance(sensors, list) or len(sensors) != 21:
        return {
            "available": False,
            "reason": "Live telemetry does not contain the 21 C-MAPSS sensor features required by the RUL model.",
            "received_sensor_count": len(sensors) if isinstance(sensors, list) else 0,
            "timestamp": row[0],
        }
    result = predict_rul(
        float(payload.get("op_setting_1", 0)),
        float(payload.get("op_setting_2", 0)),
        float(payload.get("op_setting_3", 0)),
        [float(x) for x in sensors],
    )
    return {"available": True, "machine_id": machine_id, "timestamp": row[0], **result}

@router.get("/model-registry")
def model_registry():
    return {
        "active": {"failure": "rf-industrial-v1", "rul": "rf-rul-v1", "status": "production"},
        "challenger_policy": "New models must be evaluated on ground-truth labeled failures before promotion.",
        "candidate_models": ["LightGBM", "XGBoost", "LSTM", "Transformer"],
        "promotion_guard": "No automatic model replacement is enabled; the current production model remains unchanged until a validated challenger is available.",
    }

class SimulationRequest(BaseModel):
    machine_id: str
    air_temperature: float | None = None
    process_temperature: float | None = None
    rotational_speed: float | None = None
    torque: float | None = None
    tool_wear: float | None = None

@router.post("/digital-twin/simulate")
def digital_twin_simulate(request: SimulationRequest):
    with psycopg.connect(DATABASE_URL) as conn:
        row = conn.execute(
            """SELECT machine_type, air_temperature, process_temperature,
                      rotational_speed, torque, tool_wear
               FROM sensor_readings WHERE machine_id=%s
               ORDER BY time DESC LIMIT 1""",
            (request.machine_id,),
        ).fetchone()
    if not row:
        raise HTTPException(404, f"Machine {request.machine_id} not found")
    values = {
        "machine_type": row[0],
        "air_temperature": request.air_temperature if request.air_temperature is not None else row[1],
        "process_temperature": request.process_temperature if request.process_temperature is not None else row[2],
        "rotational_speed": request.rotational_speed if request.rotational_speed is not None else row[3],
        "torque": request.torque if request.torque is not None else row[4],
        "tool_wear": request.tool_wear if request.tool_wear is not None else row[5],
    }
    result = predict_failure(**values)
    return {
        "machine_id": request.machine_id,
        "simulation_only": True,
        "warning": "This is a what-if simulation; it does not change machine controls.",
        "inputs": values,
        "predicted_result": result,
    }

@router.get("/drift/{machine_id}")
def drift(machine_id: str, recent: int = 20, baseline: int = 100):
    recent = max(5, min(recent, 100))
    baseline = max(recent + 5, min(baseline, 500))
    with psycopg.connect(DATABASE_URL) as conn:
        rows = conn.execute(
            """SELECT air_temperature, process_temperature, rotational_speed, torque, tool_wear
               FROM sensor_readings WHERE machine_id=%s
               ORDER BY time DESC LIMIT %s""",
            (machine_id, baseline),
        ).fetchall()
    if len(rows) < recent + 5:
        return {"machine_id": machine_id, "ready": False, "sample_count": len(rows)}
    recent_rows, base_rows = rows[:recent], rows[recent:]
    fields = ["air_temperature", "process_temperature", "rotational_speed", "torque", "tool_wear"]
    report = {}
    for i, name in enumerate(fields):
        recent_vals = [float(x[i]) for x in recent_rows]
        base_vals = [float(x[i]) for x in base_rows]
        base_mean = mean(base_vals)
        base_sd = pstdev(base_vals)
        shift = abs(mean(recent_vals) - base_mean) / max(base_sd, 1e-9)
        report[name] = {
            "recent_mean": round(mean(recent_vals), 4),
            "baseline_mean": round(base_mean, 4),
            "standardized_shift": round(shift, 3),
            "drift": shift >= 2.0,
        }
    return {"machine_id": machine_id, "ready": True, "report": report}
